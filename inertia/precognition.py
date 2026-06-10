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
from collections.abc import Callable, Mapping
from functools import wraps
from http import HTTPStatus
from json import loads as json_decode
from typing import Any, Concatenate, ParamSpec

from asgiref.sync import iscoroutinefunction
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.http.multipartparser import MultiPartParserError
from django.utils.cache import patch_vary_headers

from .http import _normalize_errors, errors_response

_logger = logging.getLogger("inertia_django_full_of_juice")

P = ParamSpec("P")

# Sync views only: the shipped library is synchronous by design (async
# deployments are served by gevent), so the decorator's typed surface
# statically rejects ``async def`` views and the runtime guard below raises
# for anything that slips through.
ViewFunc = Callable[Concatenate[HttpRequest, P], HttpResponse]

# Per-request extra form-constructor kwargs, mirroring the shape of Django's
# ``FormMixin.get_form_kwargs`` contract.
FormKwargs = Callable[[HttpRequest], Mapping[str, Any]]

PRECOGNITION_HEADER = "Precognition"
PRECOGNITION_VALIDATE_ONLY_HEADER = "Precognition-Validate-Only"
PRECOGNITION_SUCCESS_HEADER = "Precognition-Success"

# The same content-type match Django's test client uses for JSON payloads
# (structured suffixes like ``application/vnd.api+json`` count as JSON).
_JSON_CONTENT_TYPE_RE = re.compile(r"^application/(.+\+)?json")

# Unreadable-envelope failures from ``_parse_request_data``: JSONDecodeError
# is a ValueError subclass; MultiPartParserError is a corrupt multipart
# envelope. Kept as a named tuple constant (not an inline except-tuple) so
# the py314-targeting formatter can never rewrite the except clause into
# PEP 758 syntax, which is invalid on the supported Python ^3.12.
_MALFORMED_BODY_ERRORS = (ValueError, MultiPartParserError)


def is_precognitive(request: HttpRequest) -> bool:
    """Mirrors Laravel's ``Request::isAttemptingPrecognition()`` (exact match)."""
    return request.headers.get(PRECOGNITION_HEADER) == "true"


def validate_only_keys(request: HttpRequest) -> list[str]:
    """The ``Precognition-Validate-Only`` patterns, comma-split like Laravel's
    ``CanBePrecognitive::filterPrecognitiveRules``."""
    raw = request.headers.get(PRECOGNITION_VALIDATE_ONLY_HEADER, "")
    return [key for key in raw.split(",") if key]


def _check_request(request: HttpRequest, decorator_name: str) -> None:
    """Mirrors ``django/views/decorators/cache.py``'s ``_check_request``."""
    if not hasattr(request, "META"):
        raise TypeError(
            f"{decorator_name} didn't receive an HttpRequest. If you are "
            "decorating a classmethod, be sure to use @method_decorator."
        )


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
        # The exact parse Django's own POST path runs in
        # ``HttpRequest._load_post_and_files`` — including core's
        # ``ImmutableList`` upload-handler freeze.
        return request.parse_file_upload(request.META, request)
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
        # Documented leniency: Django's POST path hardcodes utf-8 for
        # urlencoded bodies (RFC 1866, ``_load_post_and_files``) and rejects
        # other charsets with a 400; here the request's declared encoding is
        # honored. Behavior change deferred.
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
    request: HttpRequest,
    form_class: type[BaseForm],
    form_kwargs: FormKwargs | None = None,
) -> HttpResponse:
    try:
        data, files = _parse_request_data(request)
    # The body is unreadable either way, so this answers with OUR JSON 400 —
    # keeping the ``Precognition: true`` echo the client hard-requires —
    # instead of Django's HTML 400 without it.
    except _MALFORMED_BODY_ERRORS:
        _logger.warning(
            "precognition: malformed %s body on %s %s",
            request.content_type,
            request.method,
            request.path,
        )
        return _finalize_precognition_response(
            JsonResponse({"message": "Malformed request body."}, status=400)
        )

    form = form_class(
        data=data,
        files=files or None,
        **(form_kwargs(request) if form_kwargs is not None else {}),
    )

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

    errors = _normalize_errors(form)
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
    *,
    form_kwargs: FormKwargs | None = None,
) -> Callable[[ViewFunc[P]], ViewFunc[P]]:
    """Enables the v3 Precognition contract on a view via a Django ``Form``.

    Precognitive requests are answered without ever running the view body
    (mirroring Laravel's ``PrecognitionControllerDispatcher``); everything
    else passes through, gaining ``Vary: Precognition``. Sync views only —
    the shipped library is synchronous by design (async deployments are
    served by gevent), so handing the decorator an ``async def`` view
    raises ``TypeError`` at decoration time. ``method_decorator``-compatible.

    ``form_kwargs`` mirrors Django's ``FormMixin.get_form_kwargs``: a
    per-request callable whose mapping is splatted into the form
    constructor, unblocking ``SetPasswordForm(user, …)``-style forms
    (``form_kwargs=lambda r: {"user": r.user}``) and ModelForm update flows
    (``form_kwargs=lambda r: {"instance": …}``).
    """

    def decorator(view_func: ViewFunc[P]) -> ViewFunc[P]:
        if iscoroutinefunction(view_func):
            raise TypeError(
                "precognition() does not support async views: the library "
                "is synchronous by design (serve async deployments with "
                "gevent). Use a sync view."
            )

        @wraps(view_func)
        def _view_wrapper(
            request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            _check_request(request, "precognition")
            if is_precognitive(request):
                return _handle_precognitive_request(request, form_class, form_kwargs)
            response = view_func(request, *args, **kwargs)
            patch_vary_headers(response, (PRECOGNITION_HEADER,))
            return response

        return _view_wrapper

    return decorator
