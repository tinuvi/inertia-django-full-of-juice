import logging
import re
from collections.abc import Callable, Mapping
from functools import lru_cache, wraps
from http import HTTPStatus
from json import dumps as json_encode
from typing import Any, Concatenate, ParamSpec, Union

from django.contrib.messages import get_messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import resolve_url
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme

from .helpers import deep_transform_callables
from .infinite_scroll import InfiniteScrollProp
from .prop_classes import DeferredProp, IgnoreOnFirstLoadProp, MergeableProp, OnceProp
from .settings import resolve_inertia_version, settings

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
INERTIA_SESSION_FLASH = "_inertia_flash"
INERTIA_SESSION_ERRORS = "_inertia_errors"

ErrorsInput = Union[Mapping[str, Any], BaseForm]

INERTIA_TEMPLATE = "inertia.html"
INERTIA_SSR_TEMPLATE = "inertia_ssr.html"

ALWAYS_INCLUDED_KEYS: frozenset[str] = frozenset({"errors"})


@lru_cache(maxsize=None)
def _compiled_ssr_exclude(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    """Compile the ``INERTIA_SSR_EXCLUDE`` regexes once per distinct pattern tuple.

    Mirrors Django's ``SecurityMiddleware``, which compiles
    ``SECURE_REDIRECT_EXEMPT`` a single time rather than on every request.
    Keying the cache on the pattern tuple means a settings change in tests
    (or at runtime) transparently recompiles instead of going stale.
    """
    return tuple(re.compile(pattern) for pattern in patterns)


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

    def error_bag(self) -> str:
        return self.headers.get("X-Inertia-Error-Bag", "")

    def is_inertia(self) -> bool:
        return is_inertia(self)

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

    # One-shot session state consumed while rendering, kept around so
    # InertiaMiddleware.force_refresh can re-flash it when the rendered
    # response is discarded in favor of a 409 stale-version refresh —
    # exceeding Laravel's ``onVersionChange`` session reflash (see
    # ``InertiaMiddleware.reflash_one_shot_state``).
    _pulled_flash: dict[str, Any] | None = None
    _pulled_errors: dict[str, Any] | None = None
    _pulled_clear_history: bool = False
    _pulled_preserve_fragment: bool = False
    # Shared class-level default is safe: ``build_props`` always REASSIGNS
    # ``self._rescued_props`` before appending, so the class list is never
    # mutated — the default only guards ``page_data`` paths that read it
    # before (or without) a rescue scan.
    _rescued_props: list[str] = []

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
        self._pulled_clear_history = clear_history

        preserve_fragment_flag = self.request.session.pop(
            INERTIA_SESSION_PRESERVE_FRAGMENT, False
        )
        if not isinstance(preserve_fragment_flag, bool):
            raise TypeError(
                f"Expected bool for preserve_fragment, got {type(preserve_fragment_flag).__name__}"
            )
        self._pulled_preserve_fragment = preserve_fragment_flag

        encrypt_history_flag = self.request.should_encrypt_history()

        _page: dict[str, Any] = {
            "component": self.component,
            "props": self.build_props(),
            "url": self.request.get_full_path(),
            "version": resolve_inertia_version(),
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

        _flash = self.build_flash()
        if _flash:
            _page["flash"] = _flash

        _shared_prop_keys = self.build_shared_prop_keys()
        if _shared_prop_keys:
            _page["sharedProps"] = _shared_prop_keys

        if self._rescued_props:
            _page["rescuedProps"] = list(self._rescued_props)

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

        # Always consume the one-shot session errors (Laravel's session flash
        # ages them out after one request regardless), but shared/per-request
        # ``errors`` props win the merge, keeping hand-wired recipes intact.
        session_errors = self._resolve_session_errors()
        if "errors" not in _props:
            _props["errors"] = session_errors

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

        self._rescued_props = []
        for key in list(_props.keys()):
            value = _props[key]
            should_rescue = getattr(value, "should_rescue", None)
            if not callable(should_rescue) or not should_rescue():
                continue
            try:
                _props[key] = value() if callable(value) else value
            except Exception:
                # Mirrors Laravel's PropsResolver::resolveValue (3.x): the
                # exception is reported — here via the adapter logger instead
                # of Laravel's report() — the prop is dropped from props, and
                # its key is emitted through the rescuedProps page field.
                _logger.exception(
                    "build_props: rescuing prop %r whose resolver raised; emitting it via rescuedProps",
                    key,
                )
                del _props[key]
                self._rescued_props.append(key)

        return deep_transform_callables(_props)

    def _resolve_session_errors(self) -> dict[str, Any]:
        """Pulls ``flash_errors``/``redirect_back(errors=…)`` state into the ``errors`` prop.

        Mirrors Laravel's ``Middleware::resolveValidationErrors`` (3.x):
        the session bag is consumed (pull), each field is flattened to its
        first message, and when the request carries ``X-Inertia-Error-Bag``
        the result is nested under that bag name. Always runs — the bag is
        consumed even when the view supplied its own ``errors`` prop —
        but shared/per-request ``errors`` props win the merge in
        ``build_props``, so hand-wired recipes keep working unchanged.
        """
        raw = self.request.session.pop(INERTIA_SESSION_ERRORS, None)
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise TypeError(
                f"Expected dict for session validation errors, got {type(raw).__name__}"
            )
        self._pulled_errors = raw
        flat = {
            field: (
                messages_[0] if isinstance(messages_, list) and messages_ else messages_
            )
            for field, messages_ in raw.items()
        }
        bag = self.request.error_bag()
        _logger.debug(
            "build_props: resolved session validation errors for fields=%s (error_bag=%r)",
            sorted(flat.keys()),
            bag,
        )
        return {bag: flat} if bag else flat

    def build_flash(self) -> dict[str, Any]:
        """Returns the v3 ``flash`` page field (pull semantics).

        Mirrors Laravel's ``Response::resolveFlashData`` (3.x), which pulls
        ``inertia.flash_data`` from the session on every render — partial
        reloads included. When ``INERTIA_FLASH_FROM_MESSAGES`` is enabled,
        ``django.contrib.messages`` is drained into the reserved
        ``messages`` key using the contrib.messages dict shape. Iterating
        the storage marks it used — the load-bearing mutation that lets
        ``MessageMiddleware`` clear the store on the way out.
        """
        raw = self.request.session.pop(INERTIA_SESSION_FLASH, None)
        flash_data: dict[str, Any] = {}
        if raw is not None:
            if not isinstance(raw, dict):
                raise TypeError(
                    f"Expected dict for flash data, got {type(raw).__name__}"
                )
            self._pulled_flash = raw
            flash_data = dict(raw)
        if settings.INERTIA_FLASH_FROM_MESSAGES:
            drained: list[dict[str, Any]] = []
            for message in get_messages(self.request):
                # ``message.message`` / ``message.extra_tags`` may still be
                # lazy translation proxies — ``Message._prepare`` only
                # str-coerces them when the storage serializes, which never
                # happens for messages added and drained within one request.
                # Falsy extra_tags ("" — the ``add_message`` default — or
                # None) pass through verbatim.
                extra = (
                    str(message.extra_tags)
                    if message.extra_tags
                    else message.extra_tags
                )
                drained.append(
                    {
                        "message": str(message.message),
                        "level": message.level,
                        # Replicates ``Message.tags`` (django/contrib/messages/
                        # storage/base.py) over the coerced extra_tags —
                        # reading ``message.tags`` directly would feed the
                        # lazy proxy into str.join and raise TypeError.
                        "tags": " ".join(
                            tag for tag in [extra, message.level_tag] if tag
                        ),
                        "extra_tags": extra,
                        "level_tag": message.level_tag,
                    }
                )
            if drained:
                flash_data["messages"] = drained
        if flash_data:
            _logger.debug(
                "build_flash: emitting flash keys=%s for component=%r",
                sorted(flash_data.keys()),
                self.component,
            )
        return flash_data

    def build_shared_prop_keys(self) -> list[str]:
        """Returns the v3 ``sharedProps`` page field.

        Mirrors Laravel's ``PropsResolver::resolveSharedProps`` (3.x): the
        deduped top-level key names (first dot segment) of props registered
        via ``share()``, emitted on every response — partial reloads
        included — and gated by ``INERTIA_EXPOSE_SHARED_PROP_KEYS``
        (Laravel's ``inertia.expose_shared_prop_keys``, default true).
        """
        if not settings.INERTIA_EXPOSE_SHARED_PROP_KEYS:
            return []
        keys = [str(key).split(".", 1)[0] for key in self.request.inertia]
        deduped = list(dict.fromkeys(keys))
        if deduped:
            _logger.debug(
                "build_shared_prop_keys: emitting sharedProps=%s for component=%r",
                deduped,
                self.component,
            )
        return deduped

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
            if key in self._rescued_props:
                # Mirrors Laravel's ``PropsResolver::resolveProps`` (3.x),
                # where the rescued ``continue`` precedes collectMetadata: a
                # rescued prop was dropped from ``props``, so it must not
                # advertise merge metadata for a value that never shipped.
                _logger.debug(
                    "build_merge_kinds: dropping merge metadata for %r because it was rescued",
                    key,
                )
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

    def _is_ssr_excluded(self) -> bool:
        """Return ``True`` when the request path opts out of server-side rendering.

        Matches ``request.path`` against the ``INERTIA_SSR_EXCLUDE`` regex list
        with :func:`re.search`, the same idiom Django itself uses for
        ``SECURE_REDIRECT_EXEMPT`` in ``SecurityMiddleware``. This mirrors
        Laravel's per-path SSR opt-out (``Inertia::withoutSsr`` / the gateway
        ``ExcludesSsrPaths`` contract); we deliberately diverge from Laravel's
        glob-against-full-URL-and-path matching to regex-against-``request.path``
        so the surface feels native to Django.
        """
        raw_patterns = settings.INERTIA_SSR_EXCLUDE
        if not raw_patterns:
            return False
        path = self.request.path
        for pattern in _compiled_ssr_exclude(tuple(raw_patterns)):
            if pattern.search(path):
                _logger.debug(
                    "first-load shell: skipping SSR for path=%r (matched INERTIA_SSR_EXCLUDE pattern %r)",
                    path,
                    pattern.pattern,
                )
                return True
        return False

    def build_first_load_context_and_template(
        self, data: Any
    ) -> tuple[dict[str, Any], str]:
        if settings.INERTIA_SSR_ENABLED and not self._is_ssr_excluded():
            try:
                # ``requests`` is a hard dependency; the module-level ``None`` fallback
                # only guards the optional import, so this path runs only when present.
                response = requests.post(  # pyrefly: ignore[missing-attribute]
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
        # django-stubs types ``HttpRequest.__new__`` with no parameters, so pyrefly
        # mis-resolves the ``InertiaRequest(request)`` constructor (bad-argument-count
        # / bad-assignment). The runtime ``__init__`` accepts the request as intended.
        self.request = InertiaRequest(request)  # pyrefly: ignore
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


def is_inertia(request: HttpRequest) -> bool:
    """Returns ``True`` when the request was made by the Inertia client.

    Public mirror of Laravel's ``$request->inertia()`` request macro — the
    bare ``X-Inertia`` header presence check the middleware already uses.
    """
    return "X-Inertia" in request.headers


def flash(request: HttpRequest, /, **kwargs: Any) -> None:
    """Stores one-shot flash data emitted via the v3 ``flash`` page field.

    Mirrors Laravel's ``Inertia::flash()`` (3.x): values merge with any
    already-flashed data and survive redirects, because they are only
    pulled from the session when an Inertia page actually renders.
    ``request`` is positional-only so a ``request=`` flash key stays usable.
    """
    existing = request.session.get(INERTIA_SESSION_FLASH, {})
    if not isinstance(existing, dict):
        raise TypeError(f"Expected dict for flash data, got {type(existing).__name__}")
    request.session[INERTIA_SESSION_FLASH] = {**existing, **kwargs}
    _logger.debug("flash(): stored one-shot flash keys=%s", sorted(kwargs.keys()))


def _normalize_errors(errors: ErrorsInput) -> dict[str, list[str]]:
    if isinstance(errors, BaseForm):
        return {
            field: [str(message) for message in messages_]
            for field, messages_ in errors.errors.items()
        }
    normalized: dict[str, list[str]] = {}
    for field, value in errors.items():
        if isinstance(value, str):
            messages_ = [value]
        elif isinstance(value, (list, tuple)):
            messages_ = [str(item) for item in value]
        else:
            # The ``Form.add_error`` normalization idiom: routing the value
            # through ValidationError flattens ValidationError instances to
            # their proper message strings (instead of repr noise) and
            # str-coerces scalars via its ``__iter__``.
            messages_ = ValidationError(value).messages
        if not messages_:
            # ``{"name": []}`` → omit the key at store time; an empty message
            # list would surface as an error with nothing to display
            # (``errors.get_json_data()`` never emits empty lists either).
            continue
        normalized[field] = messages_
    return normalized


def flash_errors(request: HttpRequest, errors: ErrorsInput) -> None:
    """Stores validation errors for the next Inertia render (one-shot).

    The Django mirror of Laravel's ``redirect()->withErrors()`` storage
    half: accepts a bound ``Form`` or a mapping of field → message(s),
    normalizes every field to a list of strings, and REPLACES any errors
    already flashed — Django form errors are a per-run snapshot of the
    whole submission, matching ``withErrors``'s wholesale replace.
    ``build_props`` pulls them into the ``errors`` prop on the next render
    (first message per field, nested under ``X-Inertia-Error-Bag`` when
    the request carries one).
    """
    normalized = _normalize_errors(errors)
    request.session[INERTIA_SESSION_ERRORS] = normalized
    _logger.debug(
        "flash_errors(): stored one-shot validation errors for fields=%s",
        sorted(normalized.keys()),
    )


def redirect_back(
    request: HttpRequest,
    *,
    errors: ErrorsInput | None = None,
    fallback: str = "/",
) -> HttpResponseRedirect:
    """Redirects back to the referring page, optionally flashing errors.

    Mirrors Laravel's ``Inertia::back()`` + ``->withErrors()`` pairing. We
    deliberately diverge by validating the ``Referer`` with Django's
    ``url_has_allowed_host_and_scheme`` (the ``contrib.auth`` idiom) so an
    attacker-controlled header can never produce an open redirect; unsafe
    or missing referers fall back to ``fallback``, resolved through
    ``django.shortcuts.resolve_url`` so URL names work alongside literal
    paths.
    """
    if errors is not None:
        flash_errors(request, errors)
    referer = request.META.get("HTTP_REFERER", "")
    target = resolve_url(fallback)
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        target = referer
    _logger.debug(
        "redirect_back(): redirecting to %r (errors_attached=%s)",
        target,
        errors is not None,
    )
    return HttpResponseRedirect(target)


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
