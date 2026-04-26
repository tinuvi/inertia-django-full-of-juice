import logging
from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token

from .http import inertia_redirect, location
from .settings import settings

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

        if self.is_stale(request):
            client_version = request.headers.get("X-Inertia-Version", "")
            _logger.debug(
                "middleware: stale version (client=%r, server=%r) → 409 X-Inertia-Location for hard reload",
                client_version,
                settings.INERTIA_VERSION,
            )
            return self.force_refresh(request)

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
        return "X-Inertia" in request.headers

    def is_redirect_request(self, response: HttpResponse) -> bool:
        return response.status_code in [301, 302]

    def is_fragment_redirect(self, response: HttpResponse) -> bool:
        if response.status_code not in FRAGMENT_REDIRECT_STATUSES:
            return False
        location_header = response.headers.get("Location", "")
        return "#" in location_header

    def is_stale(self, request: HttpRequest) -> bool:
        return (
            request.headers.get("X-Inertia-Version", settings.INERTIA_VERSION)
            != settings.INERTIA_VERSION
        )

    def is_stale_inertia_get(self, request: HttpRequest) -> bool:
        return request.method == "GET" and self.is_stale(request)

    def force_refresh(self, request: HttpRequest) -> HttpResponse:
        # If the storage middleware is not defined, get_messages returns an empty list
        storage = messages.get_messages(request)
        if not isinstance(storage, list):
            storage.used = False
        return location(request.build_absolute_uri())
