import logging
from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from json import dumps as json_encode
from typing import Any, Concatenate, ParamSpec

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.loader import render_to_string

from .helpers import deep_transform_callables
from .infinite_scroll import InfiniteScrollProp
from .prop_classes import DeferredProp, IgnoreOnFirstLoadProp, MergeableProp, OnceProp
from .settings import settings

try:
    # Must be early-imported so tests can patch it with
    # a mock module
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

_logger = logging.getLogger("inertia_django_full_of_juice")

P = ParamSpec("P")

INERTIA_REQUEST_ENCRYPT_HISTORY = "_inertia_encrypt_history"
INERTIA_SESSION_CLEAR_HISTORY = "_inertia_clear_history"
INERTIA_SESSION_PRESERVE_FRAGMENT = "_inertia_preserve_fragment"

INERTIA_TEMPLATE = "inertia.html"
INERTIA_SSR_TEMPLATE = "inertia_ssr.html"

ALWAYS_INCLUDED_KEYS: frozenset[str] = frozenset({"errors"})


class InertiaRequest(HttpRequest):
    def __init__(self, request: HttpRequest):
        super().__init__()
        self.__dict__.update(request.__dict__)

    @property
    def inertia(self) -> dict[str, Any]:
        inertia_attr = self.__dict__.get("inertia")
        return (
            inertia_attr.all() if inertia_attr and hasattr(inertia_attr, "all") else {}
        )

    def is_a_partial_render(self, component: str) -> bool:
        return self.headers.get("X-Inertia-Partial-Component", "") == component

    def partial_keys(self) -> list[str]:
        header = self.headers.get("X-Inertia-Partial-Data", "")
        if not header:
            return []
        return header.split(",")

    def partial_except_keys(self) -> list[str]:
        header = self.headers.get("X-Inertia-Partial-Except", "")
        if not header:
            return []
        return header.split(",")

    def reset_keys(self) -> list[str]:
        return self.headers.get("X-Inertia-Reset", "").split(",")

    def except_once_keys(self) -> list[str]:
        raw = self.headers.get("X-Inertia-Except-Once-Props", "")
        return [k for k in raw.split(",") if k]

    def is_inertia(self) -> bool:
        return "X-Inertia" in self.headers

    def should_encrypt_history(self) -> bool:
        should_encrypt = getattr(
            self, INERTIA_REQUEST_ENCRYPT_HISTORY, settings.INERTIA_ENCRYPT_HISTORY
        )
        if not isinstance(should_encrypt, bool):
            raise TypeError(
                f"Expected bool for encrypt_history, got {type(should_encrypt).__name__}"
            )
        return should_encrypt


class BaseInertiaResponseMixin:
    request: InertiaRequest
    component: str
    props: dict[str, Any]
    template_data: dict[str, Any]

    def _all_props(self) -> dict[str, Any]:
        """Returns the merged shared + per-request props.

        Mirrors Laravel's ``PropsResolver::resolve()``, which merges
        shared props first and per-request props second so that
        per-request props take precedence on key conflicts. Walking this
        merged set means registries (once / deferred / merge / scroll)
        pick up props injected via ``share(request, ...)``.
        """
        return {
            **(self.request.inertia),
            **self.props,
        }

    def _is_included_in_partial(
        self,
        key: str,
        *,
        is_partial: bool,
        partial_keys: list[str],
        partial_except_keys: list[str],
    ) -> bool:
        """Mirrors Laravel's ``PropsResolver::isIncludedInPartialMetadata``.

        On a non-partial request, every key is included. On a partial
        request, the key must appear in ``X-Inertia-Partial-Data`` (when
        set) and must not appear in ``X-Inertia-Partial-Except``.
        """
        if not is_partial:
            return True
        if partial_keys and key not in partial_keys:
            return False
        return key not in partial_except_keys

    def page_data(self) -> dict[str, Any]:
        clear_history = self.request.session.pop(INERTIA_SESSION_CLEAR_HISTORY, False)
        if not isinstance(clear_history, bool):
            raise TypeError(
                f"Expected bool for clear_history, got {type(clear_history).__name__}"
            )

        preserve_fragment_flag = self.request.session.pop(
            INERTIA_SESSION_PRESERVE_FRAGMENT, False
        )
        if not isinstance(preserve_fragment_flag, bool):
            raise TypeError(
                f"Expected bool for preserve_fragment, got {type(preserve_fragment_flag).__name__}"
            )

        encrypt_history_flag = self.request.should_encrypt_history()

        _page: dict[str, Any] = {
            "component": self.component,
            "props": self.build_props(),
            "url": self.request.get_full_path(),
            "version": settings.INERTIA_VERSION,
        }

        if encrypt_history_flag:
            _page["encryptHistory"] = True
            _logger.debug(
                "page-shell: emitting encryptHistory=True for component=%r",
                self.component,
            )

        if clear_history:
            _page["clearHistory"] = True
            _logger.debug(
                "page-shell: emitting clearHistory=True for component=%r (one-shot session flash consumed)",
                self.component,
            )

        if preserve_fragment_flag:
            _page["preserveFragment"] = True
            _logger.debug(
                "page-shell: emitting preserveFragment=True for component=%r (one-shot session flash consumed)",
                self.component,
            )

        _deferred_props = self.build_deferred_props()
        if _deferred_props:
            _page["deferredProps"] = _deferred_props

        _merge_kinds = self.build_merge_kinds()
        for field_name, values in _merge_kinds.items():
            if values:
                _page[field_name] = values

        _once_props = self.build_once_props()
        if _once_props:
            _page["onceProps"] = _once_props

        _scroll_props = self.build_scroll_props()
        if _scroll_props:
            _page["scrollProps"] = _scroll_props

        conditional_fields = sorted(
            k for k in _page if k not in {"component", "props", "url", "version"}
        )
        _logger.debug(
            "page-shell: component=%r url=%r prop_keys=%s conditional_fields=%s",
            _page["component"],
            _page["url"],
            sorted(_page["props"].keys()),
            conditional_fields,
        )
        return _page

    def build_props(self) -> Any:
        _props = self._all_props()

        _props.setdefault("errors", {})

        is_partial = self.request.is_a_partial_render(self.component)
        partial_keys = self.request.partial_keys() if is_partial else []
        partial_except_keys = self.request.partial_except_keys() if is_partial else []
        except_once_keys = self.request.except_once_keys()

        _logger.debug(
            "build_props: component=%r is_partial=%s partial_data=%s partial_except=%s except_once=%s",
            self.component,
            is_partial,
            partial_keys,
            partial_except_keys,
            except_once_keys,
        )

        for key in list(_props.keys()):
            if key in ALWAYS_INCLUDED_KEYS:
                if is_partial and key in partial_except_keys:
                    _logger.debug(
                        "build_props: dropping always-included prop %r because it is in X-Inertia-Partial-Except",
                        key,
                    )
                    del _props[key]
                continue
            if is_partial:
                if partial_keys and key not in partial_keys:
                    _logger.debug(
                        "build_props: dropping prop %r because it is not in X-Inertia-Partial-Data",
                        key,
                    )
                    del _props[key]
                    continue
                if key in partial_except_keys:
                    _logger.debug(
                        "build_props: dropping prop %r because it is in X-Inertia-Partial-Except",
                        key,
                    )
                    del _props[key]
                    continue
            else:
                if isinstance(_props[key], IgnoreOnFirstLoadProp):
                    _logger.debug(
                        "build_props: dropping prop %r on first load (IgnoreOnFirstLoad: %s)",
                        key,
                        type(_props[key]).__name__,
                    )
                    del _props[key]
                    continue

            prop_value = _props.get(key)
            if isinstance(prop_value, OnceProp):
                effective_key = prop_value.key or key
                in_except_once = effective_key in except_once_keys
                in_partial_data = is_partial and key in partial_keys
                if in_except_once and prop_value.fresh:
                    _logger.debug(
                        "build_props: once prop %r (registry key=%r) survives X-Inertia-Except-Once-Props because fresh=True",
                        key,
                        effective_key,
                    )
                elif in_except_once and in_partial_data:
                    _logger.debug(
                        "build_props: once prop %r (registry key=%r) survives X-Inertia-Except-Once-Props because it is in X-Inertia-Partial-Data",
                        key,
                        effective_key,
                    )
                elif in_except_once and not prop_value.fresh:
                    _logger.debug(
                        "build_props: skipping once prop %r (registry key=%r) because it is in X-Inertia-Except-Once-Props",
                        key,
                        effective_key,
                    )
                    del _props[key]

        return deep_transform_callables(_props)

    def build_once_props(self) -> dict[str, dict[str, Any]]:
        is_partial = self.request.is_a_partial_render(self.component)
        partial_keys = self.request.partial_keys() if is_partial else []
        partial_except_keys = self.request.partial_except_keys() if is_partial else []
        reset = set(self.request.reset_keys())

        _once_props: dict[str, dict[str, Any]] = {}
        for key, prop in self._all_props().items():
            if not isinstance(prop, OnceProp):
                continue
            if key in reset:
                _logger.debug(
                    "build_once_props: dropping once registry entry for %r because it is in X-Inertia-Reset",
                    key,
                )
                continue
            if not self._is_included_in_partial(
                key,
                is_partial=is_partial,
                partial_keys=partial_keys,
                partial_except_keys=partial_except_keys,
            ):
                continue
            effective_key = prop.key or key
            _once_props[effective_key] = {
                "prop": key,
                "expiresAt": prop.expires_at,
            }
        if _once_props:
            _logger.debug("build_once_props: emitting onceProps=%s", _once_props)
        return _once_props

    def build_deferred_props(self) -> dict[str, Any] | None:
        if self.request.is_a_partial_render(self.component):
            _logger.debug(
                "build_deferred_props: suppressing deferredProps on partial render of component=%r",
                self.component,
            )
            return None

        _deferred_props: dict[str, Any] = {}
        for key, prop in self._all_props().items():
            if isinstance(prop, DeferredProp):
                _deferred_props.setdefault(prop.group, []).append(key)

        if _deferred_props:
            _logger.debug(
                "build_deferred_props: emitting deferredProps=%s for component=%r",
                _deferred_props,
                self.component,
            )
        return _deferred_props

    def build_scroll_props(self) -> dict[str, dict[str, Any]]:
        """Returns the v3 ``scrollProps`` registry.

        Walks the merged shared + per-request props for
        :class:`InfiniteScrollProp` instances and emits one entry per
        prop with the four metadata keys plus a ``reset`` boolean derived
        from ``X-Inertia-Reset``. The entry is suppressed when the prop
        is filtered out by ``X-Inertia-Partial-Data`` /
        ``X-Inertia-Partial-Except`` — mirroring how the underlying
        prop value would not survive into the response.
        """
        is_partial = self.request.is_a_partial_render(self.component)
        partial_keys = self.request.partial_keys() if is_partial else []
        partial_except_keys = self.request.partial_except_keys() if is_partial else []
        reset = set(self.request.reset_keys())

        out: dict[str, dict[str, Any]] = {}
        for key, prop in self._all_props().items():
            if not isinstance(prop, InfiniteScrollProp):
                continue
            if not self._is_included_in_partial(
                key,
                is_partial=is_partial,
                partial_keys=partial_keys,
                partial_except_keys=partial_except_keys,
            ):
                continue
            metadata = prop.scroll_metadata()
            metadata["reset"] = key in reset
            out[key] = metadata
        if out:
            _logger.debug(
                "build_scroll_props: emitting scrollProps=%s for component=%r",
                out,
                self.component,
            )
        return out

    def build_merge_kinds(self) -> dict[str, list[str]]:
        """Returns the four merge-metadata arrays. Empty arrays mean "don't emit"."""
        out: dict[str, list[str]] = {
            "mergeProps": [],
            "prependProps": [],
            "deepMergeProps": [],
            "matchPropsOn": [],
        }
        is_partial = self.request.is_a_partial_render(self.component)
        partial_keys = self.request.partial_keys() if is_partial else []
        partial_except_keys = self.request.partial_except_keys() if is_partial else []
        reset = set(self.request.reset_keys())

        for key, prop in self._all_props().items():
            if not isinstance(prop, MergeableProp):
                continue
            if not prop.should_merge():
                continue
            if key in reset:
                _logger.debug(
                    "build_merge_kinds: dropping merge metadata for %r because it is in X-Inertia-Reset",
                    key,
                )
                continue
            if not self._is_included_in_partial(
                key,
                is_partial=is_partial,
                partial_keys=partial_keys,
                partial_except_keys=partial_except_keys,
            ):
                continue
            strategy = prop.merge_strategy()
            if strategy == "append":
                out["mergeProps"].append(key)
            elif strategy == "prepend":
                out["prependProps"].append(key)
            elif strategy == "deep":
                out["deepMergeProps"].append(key)
            for path in prop.match_on():
                out["matchPropsOn"].append(f"{key}.{path}")
        if any(out.values()):
            _logger.debug(
                "build_merge_kinds: mergeProps=%s prependProps=%s deepMergeProps=%s matchPropsOn=%s",
                out["mergeProps"],
                out["prependProps"],
                out["deepMergeProps"],
                out["matchPropsOn"],
            )
        return out

    def build_first_load(self, data: Any) -> str:
        context, template = self.build_first_load_context_and_template(data)

        try:
            layout = settings.INERTIA_LAYOUT
            if not layout:
                raise AttributeError("INERTIA_LAYOUT is set, but has a falsy value")
        except AttributeError as ae:
            raise ImproperlyConfigured(
                "INERTIA_LAYOUT must be set in your Django settings"
            ) from ae

        return render_to_string(
            template,
            {
                "inertia_layout": layout,
                **context,
            },
            self.request,
            using=None,
        )

    def build_first_load_context_and_template(
        self, data: Any
    ) -> tuple[dict[str, Any], str]:
        if settings.INERTIA_SSR_ENABLED:
            try:
                response = requests.post(
                    f"{settings.INERTIA_SSR_URL}/render",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                _logger.debug(
                    "first-load shell: SSR render succeeded for component=%r",
                    self.component,
                )
                return {
                    **response.json(),
                    **self.template_data,
                }, INERTIA_SSR_TEMPLATE
            except Exception:
                _logger.exception("SSR render request failed")

        # Escape characters that would let an attacker break out of the
        # `<script type="application/json">` block in the v3 page-shell.
        # ``/`` is escaped so a literal ``</script>`` inside a prop value can
        # never close the wrapping element on legacy/non-conforming parsers.
        safe_data = (
            data.replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
            .replace("/", "\\u002f")
        )
        escaped_count = len(safe_data) - len(data)
        _logger.debug(
            "first-load shell: rendering inline JSON for component=%r (raw_len=%d, escaped_chars_added=%d)",
            self.component,
            len(data),
            escaped_count,
        )
        return {
            "page": safe_data,
            **(self.template_data),
        }, INERTIA_TEMPLATE


class InertiaResponse(BaseInertiaResponseMixin, HttpResponse):
    json_encoder = None

    def __init__(
        self,
        request: HttpRequest,
        component: str,
        props: dict[str, Any] | None = None,
        template_data: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.request = InertiaRequest(request)
        self.component = component
        self.props = props or {}
        self.template_data = template_data or {}
        _headers = headers or {}

        data = json_encode(
            self.page_data(),
            cls=self.json_encoder or settings.INERTIA_JSON_ENCODER,
        )

        if self.request.is_inertia():
            _headers = {
                **_headers,
                "Vary": "X-Inertia",
                "X-Inertia": "true",
                "Content-Type": "application/json",
            }
            content = data
        else:
            content = self.build_first_load(data)

        if args:
            super().__init__(
                *args,
                headers=_headers,
                **kwargs,
            )
        else:
            super().__init__(
                content=content,
                headers=_headers,
                **kwargs,
            )


def render(
    request: HttpRequest,
    component: str,
    props: dict[str, Any] | None = None,
    template_data: dict[str, Any] | None = None,
) -> InertiaResponse:
    return InertiaResponse(request, component, props or {}, template_data or {})


def location(location: str) -> HttpResponse:
    _logger.debug("location(): emitting 409 with X-Inertia-Location=%r", location)
    return HttpResponse(
        "",
        status=HTTPStatus.CONFLICT,
        headers={
            "X-Inertia-Location": location,
        },
    )


def inertia_redirect(url: str) -> HttpResponse:
    _logger.debug("inertia_redirect(): emitting 409 with X-Inertia-Redirect=%r", url)
    return HttpResponse(
        "",
        status=HTTPStatus.CONFLICT,
        headers={
            "X-Inertia-Redirect": url,
        },
    )


def encrypt_history(request: HttpRequest, value: bool = True) -> None:
    _logger.debug("encrypt_history(): set request flag to %s", value)
    setattr(request, INERTIA_REQUEST_ENCRYPT_HISTORY, value)


def clear_history(request: HttpRequest) -> None:
    _logger.debug("clear_history(): set session flash flag (one-shot)")
    request.session[INERTIA_SESSION_CLEAR_HISTORY] = True


def preserve_fragment(request: HttpRequest) -> None:
    _logger.debug("preserve_fragment(): set session flash flag (one-shot)")
    request.session[INERTIA_SESSION_PRESERVE_FRAGMENT] = True


def errors_response(
    errors: dict[str, Any],
    message: str = "The given data was invalid.",
    status: int = 422,
) -> JsonResponse:
    _logger.debug(
        "errors_response(): status=%d fields=%s message=%r",
        status,
        sorted(errors.keys()),
        message,
    )
    return JsonResponse(
        {"message": message, "errors": errors},
        status=status,
    )


def inertia(
    component: str,
) -> Callable[
    [
        Callable[
            Concatenate[HttpRequest, P],
            HttpResponse | InertiaResponse | dict[str, Any],
        ]
    ],
    Callable[Concatenate[HttpRequest, P], HttpResponse],
]:
    def decorator(
        func: Callable[
            Concatenate[HttpRequest, P],
            HttpResponse | InertiaResponse | dict[str, Any],
        ],
    ) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
        @wraps(func)
        def process_inertia_response(
            request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            props = func(request, *args, **kwargs)

            # if a response is returned, return it
            if isinstance(props, HttpResponse):
                return props

            return InertiaResponse(request, component, props)

        return process_inertia_response

    return decorator
