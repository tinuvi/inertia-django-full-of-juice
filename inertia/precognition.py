"""Server-side support for Inertia v3 Precognition (live form validation).

In the Laravel ecosystem this behavior lives in ``laravel/framework``
(``HandlePrecognitiveRequests`` + the precognition dispatchers), not in
``inertia-laravel`` — the Django adapter absorbs that framework-level
surface here as a per-view decorator, the Django equivalent of Laravel's
per-route ``precognitive`` middleware alias.

Wire contract (v3 protocol, "the-protocol" §Precognition):

* request: ``Precognition: true`` plus an optional comma-separated
  ``Precognition-Validate-Only`` field list (``*`` matches one dot segment);
* success: ``204 No Content`` with ``Precognition-Success: true``;
* failure: ``422`` JSON ``{"message": …, "errors": {field: [messages]}}``;
* every response on a precognition-enabled view — precognitive or not —
  must vary on (and, when precognitive, echo) the ``Precognition`` header,
  or the client throws "Did not receive a Precognition response".
"""

import logging
import re
from collections.abc import Awaitable, Callable
from functools import wraps
from http import HTTPStatus
from json import loads as json_decode
from typing import Any, Concatenate, ParamSpec, cast

from asgiref.sync import iscoroutinefunction
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.http.multipartparser import MultiPartParser
from django.utils.cache import patch_vary_headers

from .http import errors_response

_logger = logging.getLogger("inertia_django_full_of_juice")

P = ParamSpec("P")

PRECOGNITION_HEADER = "Precognition"
PRECOGNITION_VALIDATE_ONLY_HEADER = "Precognition-Validate-Only"
PRECOGNITION_SUCCESS_HEADER = "Precognition-Success"

# The same content-type match Django's test client uses for JSON payloads
# (structured suffixes like ``application/vnd.api+json`` count as JSON).
_JSON_CONTENT_TYPE_RE = re.compile(r"^application/(.+\+)?json")

ViewFunc = Callable[Concatenate[HttpRequest, P], HttpResponse]


def is_precognitive(request: HttpRequest) -> bool:
    """Mirrors Laravel's ``Request::isAttemptingPrecognition()`` (exact match)."""
    return request.headers.get(PRECOGNITION_HEADER) == "true"


def validate_only_keys(request: HttpRequest) -> list[str]:
    """The ``Precognition-Validate-Only`` patterns, comma-split like Laravel's
    ``CanBePrecognitive::filterPrecognitiveRules``."""
    raw = request.headers.get(PRECOGNITION_VALIDATE_ONLY_HEADER, "")
    return [key for key in raw.split(",") if key]


def _matches_validate_only(field: str, patterns: list[str]) -> bool:
    """Mirrors Laravel's ``shouldValidatePrecognitiveAttribute``: each pattern
    is regex-quoted with ``*`` rewritten to ``[^.]+`` (one dot segment)."""
    for pattern in patterns:
        regex = re.escape(pattern).replace(r"\*", r"[^.]+")
        if re.fullmatch(regex, field):
            return True
    return False


def _parse_request_data(
    request: HttpRequest,
) -> tuple[Any, Any]:
    """Extracts (data, files) the way the v3 client serializes validate requests:
    query params for GET/DELETE, JSON bodies by default otherwise, multipart
    only when file validation is enabled client-side."""
    method = (request.method or "GET").upper()
    if method in ("GET", "DELETE"):
        return request.GET, None

    content_type = request.content_type or ""
    if content_type == "multipart/form-data":
        if method == "POST":
            return request.POST, request.FILES
        data, files = MultiPartParser(
            request.META, request, request.upload_handlers, request.encoding
        ).parse()
        return data, files
    if _JSON_CONTENT_TYPE_RE.match(content_type):
        body = request.body
        if not body:
            return {}, None
        parsed = json_decode(body)
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed, None
    if content_type == "application/x-www-form-urlencoded":
        if method == "POST":
            return request.POST, None
        return QueryDict(request.body, encoding=request.encoding), None
    return (request.POST, request.FILES) if method == "POST" else ({}, None)


def _finalize_precognition_response(response: HttpResponse) -> HttpResponse:
    """Every precognitive response must echo ``Precognition: true`` (the client
    throws otherwise) and vary on the header, mirroring Laravel's
    ``HandlePrecognitiveRequests::handle`` response tap."""
    response[PRECOGNITION_HEADER] = "true"
    patch_vary_headers(response, (PRECOGNITION_HEADER,))
    return response


def _handle_precognitive_request(
    request: HttpRequest, form_class: type[BaseForm]
) -> HttpResponse:
    try:
        data, files = _parse_request_data(request)
    except ValueError:  # JSONDecodeError is a ValueError subclass
        _logger.warning(
            "precognition: malformed %s body on %s %s",
            request.content_type,
            request.method,
            request.path,
        )
        return _finalize_precognition_response(
            JsonResponse({"message": "Malformed request body."}, status=400)
        )

    form = form_class(data=data, files=files or None)

    only = validate_only_keys(request)
    if only:
        # Mirrors Laravel's validator rule filtering by restricting the form
        # *instance*'s fields — the mutation Django's own docs sanction
        # ("Instances should always modify self.fields") — so untouched
        # required fields never false-error and their validators never run.
        for name in list(form.fields):
            if not _matches_validate_only(name, only):
                form.fields.pop(name)

    if form.is_valid():
        _logger.debug(
            "precognition: validation passed for %s %s (validate_only=%s)",
            request.method,
            request.path,
            only,
        )
        response: HttpResponse = HttpResponse(status=HTTPStatus.NO_CONTENT)
        response[PRECOGNITION_SUCCESS_HEADER] = "true"
        return _finalize_precognition_response(response)

    errors = {
        field: [str(message) for message in messages_]
        for field, messages_ in form.errors.items()
    }
    _logger.debug(
        "precognition: validation failed for %s %s fields=%s (validate_only=%s)",
        request.method,
        request.path,
        sorted(errors.keys()),
        only,
    )
    return _finalize_precognition_response(errors_response(errors))


def precognition(
    form_class: type[BaseForm],
) -> Callable[[ViewFunc[P]], ViewFunc[P]]:
    """Enables the v3 Precognition contract on a view via a Django ``Form``.

    Precognitive requests are answered without ever running the view body
    (mirroring Laravel's ``PrecognitionControllerDispatcher``); everything
    else passes through, gaining ``Vary: Precognition``. Supports both sync
    and async views (Django's own dual-wrapper decorator idiom) and is
    ``method_decorator``-compatible.
    """

    def decorator(view_func: ViewFunc[P]) -> ViewFunc[P]:
        if iscoroutinefunction(view_func):
            # iscoroutinefunction is a runtime guard, not a type narrower.
            async_view = cast(
                "Callable[Concatenate[HttpRequest, P], Awaitable[HttpResponse]]",
                view_func,
            )

            async def _view_wrapper(
                request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
            ) -> HttpResponse:
                if is_precognitive(request):
                    return _handle_precognitive_request(request, form_class)
                response = await async_view(request, *args, **kwargs)
                patch_vary_headers(response, (PRECOGNITION_HEADER,))
                return response

        else:

            def _view_wrapper(
                request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
            ) -> HttpResponse:
                if is_precognitive(request):
                    return _handle_precognitive_request(request, form_class)
                response = view_func(request, *args, **kwargs)
                patch_vary_headers(response, (PRECOGNITION_HEADER,))
                return response

        return wraps(view_func)(_view_wrapper)  # pyrefly: ignore[bad-return]

    return decorator
