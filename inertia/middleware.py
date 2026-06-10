import logging
from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token

from .http import (
    INERTIA_SESSION_CLEAR_HISTORY,
    INERTIA_SESSION_ERRORS,
    INERTIA_SESSION_FLASH,
    INERTIA_SESSION_PRESERVE_FRAGMENT,
    inertia_redirect,
    is_inertia,
    location,
)
from .settings import resolve_inertia_version

FRAGMENT_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

_logger = logging.getLogger("inertia_django_full_of_juice")


class InertiaMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Inertia requests don't ever render templates, so they skip the typical Django
        # CSRF path. We'll manually add a CSRF token for every request here.
        get_token(request)

        is_inertia = self.is_inertia_request(request)
        _logger.debug(
            "middleware: method=%s path=%r is_inertia=%s downstream_status=%s",
            request.method,
            request.get_full_path(),
            is_inertia,
            response.status_code,
        )

        if not is_inertia:
            return response

        if self.is_fragment_redirect(response):
            location_header = response.headers.get("Location", "")
            _logger.debug(
                "middleware: fragment redirect detected (status=%s, location=%r) → rewriting to 409 X-Inertia-Redirect",
                response.status_code,
                location_header,
            )
            return inertia_redirect(location_header)

        if self.is_non_post_redirect(request, response):
            _logger.debug(
                "middleware: converting %s redirect from %s to 303 (per v3 method-conversion contract)",
                request.method,
                response.status_code,
            )
            response.status_code = 303

        if self.is_stale_inertia_get(request):
            client_version = request.headers.get("X-Inertia-Version", "")
            _logger.debug(
                "middleware: stale version (client=%r, server=%r) → 409 X-Inertia-Location for hard reload",
                client_version,
                resolve_inertia_version(),
            )
            return self.force_refresh(request, response)

        return response

    def is_non_post_redirect(
        self, request: HttpRequest, response: HttpResponse
    ) -> bool:
        return self.is_redirect_request(response) and request.method in [
            "PUT",
            "PATCH",
            "DELETE",
        ]

    def is_inertia_request(self, request: HttpRequest) -> bool:
        return is_inertia(request)

    def is_redirect_request(self, response: HttpResponse) -> bool:
        return response.status_code in [301, 302]

    def is_fragment_redirect(self, response: HttpResponse) -> bool:
        if response.status_code not in FRAGMENT_REDIRECT_STATUSES:
            return False
        location_header = response.headers.get("Location", "")
        return "#" in location_header

    def is_stale(self, request: HttpRequest) -> bool:
        server_version = resolve_inertia_version()
        return (
            request.headers.get("X-Inertia-Version", server_version) != server_version
        )

    def is_stale_inertia_get(self, request: HttpRequest) -> bool:
        return request.method == "GET" and self.is_stale(request)

    def force_refresh(
        self, request: HttpRequest, response: HttpResponse | None = None
    ) -> HttpResponse:
        # If the storage middleware is not defined, get_messages returns an empty list
        storage = messages.get_messages(request)
        if not isinstance(storage, list):
            storage.used = False
        self.reflash_one_shot_state(request, response)
        return location(request.build_absolute_uri())

    def reflash_one_shot_state(
        self, request: HttpRequest, response: HttpResponse | None
    ) -> None:
        """Restores one-shot session state consumed by the discarded response.

        The stale-version 409 throws away a fully rendered page, so anything
        ``page_data`` already popped from the session (flash data, validation
        errors, the clearHistory / preserveFragment flags) would silently die
        with it. The rendered response stashes what it pulled, and we write it
        back so the client's follow-up hard reload still delivers it. This
        exceeds Laravel's ``Middleware::onVersionChange`` reflash, satisfying
        the protocol's reflash mandate: Laravel's ``Store::reflash()`` only
        re-marks flash key *names*, and cannot restore values the render
        already pulled (``ResponseFactory::pullFlashed`` keeps no stash).
        """
        pulled_flash = getattr(response, "_pulled_flash", None)
        if pulled_flash:
            current_flash = request.session.get(INERTIA_SESSION_FLASH, {})
            if not isinstance(current_flash, dict):
                current_flash = {}
            request.session[INERTIA_SESSION_FLASH] = {**pulled_flash, **current_flash}
            _logger.debug(
                "force_refresh: re-flashed %d flash key(s) consumed by the discarded stale response",
                len(pulled_flash),
            )

        pulled_errors = getattr(response, "_pulled_errors", None)
        if pulled_errors:
            current_errors = request.session.get(INERTIA_SESSION_ERRORS, {})
            if not isinstance(current_errors, dict):
                current_errors = {}
            request.session[INERTIA_SESSION_ERRORS] = {
                **pulled_errors,
                **current_errors,
            }
            _logger.debug(
                "force_refresh: re-flashed validation errors for fields=%s consumed by the discarded stale response",
                sorted(pulled_errors.keys()),
            )

        if getattr(response, "_pulled_clear_history", False):
            request.session[INERTIA_SESSION_CLEAR_HISTORY] = True
            _logger.debug(
                "force_refresh: re-flashed one-shot clearHistory flag consumed by the discarded stale response"
            )

        if getattr(response, "_pulled_preserve_fragment", False):
            request.session[INERTIA_SESSION_PRESERVE_FRAGMENT] = True
            _logger.debug(
                "force_refresh: re-flashed one-shot preserveFragment flag consumed by the discarded stale response"
            )
