# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-10

### Added
- `inertia.precognition` module with a `@precognition(FormClass)` view decorator and `is_precognitive(request)` / `validate_only_keys(request)` helpers, implementing the v3 Precognition wire contract: precognitive requests (`Precognition: true`) are answered without running the view body — `204 No Content` + `Precognition-Success: true` on success, `422` `{"message", "errors": {field: [messages]}}` on failure — every response gains `Vary: Precognition` (via `patch_vary_headers`), and precognitive responses echo `Precognition: true` (the v3 client throws without it). `Precognition-Validate-Only` scoping pops unlisted fields off the form instance before validation (with Laravel's `*` = one-dot-segment wildcard semantics); bodies are parsed as the client sends them (JSON by default, query params for GET/DELETE, multipart/urlencoded for POST and non-POST alike). Supports sync and async views via the dual-wrapper idiom (`asgiref.sync.iscoroutinefunction`) and is `method_decorator`-compatible. In Laravel this surface lives in `laravel/framework` (`HandlePrecognitiveRequests`, `Foundation/Precognition.php`, the precognition dispatchers), not `inertiajs/inertia-laravel` — the decorator is the Django mirror of the per-route `precognitive` middleware alias.
- `flash(request, **kwargs)` and the v3 `flash` page-object field: one-shot data merged into the session (`_inertia_flash`) and pulled at render time on every Inertia render, partial reloads included — mirroring `inertiajs/inertia-laravel@3.x` `ResponseFactory::flash()` / `Response::resolveFlashData()` (session key `inertia.flash_data`, pull semantics). Omitted when empty.
- `INERTIA_FLASH_FROM_MESSAGES` setting (default `False`): when enabled, each render drains `django.contrib.messages` (read-only iteration; `MessageMiddleware`'s exit path clears the store) into `flash["messages"]` as `{message, level, tags, extra_tags, level_tag}` dicts. Render-time draining means partial reloads and multi-hop redirect chains can no longer consume a pending message without delivering it — the failure modes of the eager per-request middleware recipe.
- Built-in validation-errors flow: `flash_errors(request, errors)` (accepts a bound `django.forms` form or a `{field: message(s)}` mapping, normalized to lists of strings) stores one-shot errors in the session (`_inertia_errors`); the next render pulls them into the `errors` prop with first-message-per-field flattening and `X-Inertia-Error-Bag` nesting, mirroring `inertiajs/inertia-laravel@3.x` `Middleware::resolveValidationErrors`. Shared or per-render `errors` props win over the session flow (and the session bag still ages out), so pre-0.5.0 hand-wired recipes keep working unchanged. Intentional divergence: errors are stored as a single default bag (Django has no `ViewErrorBag`), so bag nesting is driven purely by the request header.
- `back(request, *, errors=None, fallback="/")` — redirect-to-referrer helper mirroring Laravel's `Inertia::back()` + `redirect()->withErrors()` pairing. Intentional divergence: the `Referer` is validated with Django's `url_has_allowed_host_and_scheme` (the `contrib.auth` idiom) before use, so the attacker-controlled header can never produce an open redirect; unsafe or missing referrers use `fallback`.
- `defer(..., rescue=True)` and the v3 `rescuedProps` page-object field, mirroring `inertiajs/inertia-laravel@3.x` `ResponseFactory::defer($callback, $group, $rescue)` and `PropsResolver::resolveValue()`: when a rescuable prop's resolver raises, the exception is reported (here via `logger.exception` on the `inertia_django_full_of_juice` logger — the Django mirror of Laravel's `report()`), the prop is dropped from `props`, and its key is emitted in `rescuedProps` (only when non-empty). The check is duck-typed on `should_rescue()` like Laravel's `Rescuable` interface, so custom prop classes can opt in.
- v3 `sharedProps` page-object field and `INERTIA_EXPOSE_SHARED_PROP_KEYS` setting (default `True`): every response lists the deduped top-level key names (first dot segment) registered via `share()`, which the client uses to carry shared props over during instant visits — mirroring `inertiajs/inertia-laravel@3.x` `PropsResolver::resolveSharedProps()` and the `inertia.expose_shared_prop_keys` config. Intentional divergence: the auto-injected `errors` prop is not listed (Laravel lists it because its middleware *shares* errors; ours injects them at build time).
- `is_inertia(request)` public helper — the bare `X-Inertia` header check, mirroring Laravel's `$request->inertia()` request macro.

### Fixed
- `from inertia import encrypt_history, clear_history` now works as the README has always documented — both helpers (and the new ones) are exported from `inertia/__init__.py`; previously the documented imports raised `ImportError`.
- One-shot session state now survives the `409` stale-asset refresh. `page_data()` stashes everything it pops from the session (`flash`, validation errors, the `clearHistory` / `preserveFragment` flags) on the rendered response, and `InertiaMiddleware.force_refresh` re-flashes it when that response is discarded for a `409 X-Inertia-Location` hard reload — extending the existing `storage.used = False` messages reset and mirroring the session reflash in Laravel's `Middleware::onVersionChange`. Previously a `clear_history()` or `preserve_fragment()` call (and any 0.5.0 flash/errors) pending at an asset-version bump died silently with the discarded response.

## [0.4.0] - 2026-05-30

### Added
- `INERTIA_SSR_EXCLUDE` setting — a list of regex pattern strings matched (via `re.search`) against `request.path`. When a request path matches any pattern, `inertia/http.py` skips the SSR render call in `build_first_load_context_and_template` and falls back to the inline-JSON client-side shell, mirroring Inertia v3's "Excluding Routes from SSR". Patterns are compiled once per distinct pattern tuple (`_compiled_ssr_exclude`), following Django's own `SECURE_REDIRECT_EXEMPT` idiom in `SecurityMiddleware`. Emits a `first-load shell: skipping SSR for path=… (matched INERTIA_SSR_EXCLUDE pattern …)` DEBUG record on the `inertia_django_full_of_juice` logger. Defaults to `[]` (no exclusions). Mirrors Laravel's per-path SSR opt-out (`Inertia::withoutSsr` / the gateway `ExcludesSsrPaths` contract); diverges deliberately from Laravel's glob-against-full-URL-and-path matching to regex-against-`request.path` to match Django convention.
- `inertia/apps.py` with an `InertiaConfig` app config that registers a Django system check (`inertia.E001`) validating that every `INERTIA_SSR_EXCLUDE` entry is a compilable regex. A malformed pattern is reported at startup (`runserver` / `manage.py check` / `migrate`) instead of raising at request time.
- `INERTIA_VERSION` may now be a zero-arg callable in addition to a plain value. It is resolved once per request by the new `inertia.settings.resolve_inertia_version`, used both for the page-object `version` field (`inertia/http.py`) and the stale-asset comparison (`inertia/middleware.py`). Mirrors Laravel's version closure (`inertiajs/inertia-laravel@3.x` `src/ResponseFactory.php` `getVersion()`), letting consumers derive the asset version dynamically — e.g. `INERTIA_VERSION = lambda: staticfiles_storage.manifest_hash` to auto-bust on every deploy (Django 4.2+ with `ManifestStaticFilesStorage`).

### Fixed
- The `409 Conflict` + `X-Inertia-Location` stale-asset hard reload is now sent only for `GET` requests. `InertiaMiddleware` previously issued it on any method, so a stale `X-Inertia-Version` on a `POST` / `PUT` / `PATCH` / `DELETE` was wrongly converted to a 409. Per the v3 protocol these responses are GET-only — the follow-up GET after a redirect carries the version check — so the middleware now gates on the existing `is_stale_inertia_get`.
- `INERTIA_VERSION` is now cast to a string before being emitted and compared. A non-string value (e.g. an `int`) previously leaked a non-string into the page-object `version` JSON *and* made every `GET` stale — the string `X-Inertia-Version` header could never equal a non-string setting — forcing a 409 hard-reload loop. `None` now resolves to `""`, which disables asset versioning (the v3 client omits `X-Inertia-Version` when `page.version` is falsy), matching Laravel's `(string) null` cast in `ResponseFactory::getVersion()`.

## [0.3.1] - 2026-04-26

### Changed
- `inertia/http.py`, `inertia/middleware.py`, and `inertia/infinite_scroll.py` now emit DEBUG records on the `inertia_django_full_of_juice` logger for every protocol decision: partial-data / partial-except / except-once filtering, once-prop survival vs. skip, deferred-group emission and partial-render suppression, merge / prepend / deep-merge / scroll metadata emission and reset-driven removal, infinite-scroll merge-intent resolution, fragment-redirect rewrite, 302→303 method conversion, stale-version refresh, and one-shot consumption of `clearHistory` / `preserveFragment` session flags. The module-level logger handles are renamed `_logger` to mark them as private. The records are pinned by tests in `inertia/tests/test_logging.py` so the phrasing is a stable contract.

## [0.3.0] - 2026-04-26

Adds support for the [Inertia.js v3 protocol](https://inertiajs.com/docs/v3/core-concepts/the-protocol.md).

### Added
- `inertia.once(...)` and `OnceProp` for v3 once-props (skip resolving on cached client). Supports `key`, `fresh`, `expires_in` (`timedelta` or seconds) and `expires_at` (`datetime` or unix-ms) ergonomic options.
- `inertia.prepend(...)` and `PrependProp` for prepend-merge.
- `inertia.deep_merge(...)` and `DeepMergeProp` for deep-object merging.
- `match_on=` keyword on `merge()`, `prepend()`, `deep_merge()`, and `defer()` — emits `matchPropsOn` dot-paths so the v3 client can dedup merging by item id.
- `inertia.infinite_scroll(...)` and `InfiniteScrollProp` — server helper that reads `X-Inertia-Infinite-Scroll-Merge-Intent` at render time and emits the `scrollProps` page-object field with `pageName` / `previousPage` / `nextPage` / `currentPage` / `reset`.
- `inertia.preserve_fragment(request)` (session-flash) — emits `preserveFragment: true` on the next response so the v3 client carries the request URL fragment to the redirect target.
- `inertia.inertia_redirect(url)` — `409 Conflict` + `X-Inertia-Redirect` helper.
- `inertia.errors_response(errors, message=, status=)` — `422` JSON with `{message, errors}` body for `useHttp` (non-Inertia XHR) validation responses.
- Auto-injected `props.errors = {}` on every Inertia response when not already provided by the user. Does not clobber `share(request, errors=...)`. `errors` is exempt from `X-Inertia-Partial-Data` filtering so it survives partial reloads.
- Honor the `X-Inertia-Partial-Except` request header (precedence over `X-Inertia-Partial-Data`).

### Changed
- The page-object fields `encryptHistory`, `clearHistory`, and `preserveFragment` are now emitted only when `true` (v3 only-when-true convention). Test helpers updated accordingly.
- `InertiaMiddleware` now converts any redirect response whose `Location` contains a `#fragment` on an Inertia request into a `409 + X-Inertia-Redirect` so the v3 client preserves the fragment.
- The first-load page shell now emits `<script data-page="app" type="application/json">…</script>` followed by a bare `<div id="app"></div>`, replacing the legacy `<div id="app" data-page="…">` form. The v3 client refuses to boot from the legacy attribute. The page-data JSON has `<`, `>`, and `&` escaped as `<` / `>` / `&` to prevent script-context breakouts. `inertia_div()` test helper updated accordingly.

### Added
- `sample_project/` — thin Django + React app exercising every server helper (`once`, `defer`, `merge`, `prepend`, `deep_merge`, `infinite_scroll`, `preserve_fragment`, `inertia_redirect`, `useForm` validation).

## [0.2.0] - 2026-04-25

Type-hint and toolchain refresh.

### Added
- `inertia/py.typed` marker (PEP 561) so downstream type checkers honor the package's inline annotations.
- Generic `T` parameter on `CallableProp`, `OptionalProp`, `DeferredProp`, and `MergeProp`, propagated through the `optional()`, `defer()`, `merge()`, and `lazy()` helpers.
- `ParamSpec` + `Concatenate` on the `@inertia` decorator so wrapped view signatures flow through to call sites.

### Changed
- Logger is now `logging.getLogger("inertia_django_full_of_juice")` (replaces `getLogger(__name__)`).
- Toolchain bumped to Python 3.14: `ruff`, `mypy`, `django-stubs`, and `types-requests` upgraded; `target-version` aligned in ruff and mypy.
- `poetry.lock` is now committed for reproducible builds.
- Dockerfile no longer installs `git`.

## [0.1.0] - 2026-02-24

Initial release of the `inertia-django-full-of-juice` fork (forked from `inertia-django`).

### Added
- Static type hints throughout the codebase, verified with `mypy`, plus a `mypy` job in CI (#85).
- Logging when SSR render requests fail, surfacing previously-silent fallbacks to client-side rendering (#89).
- Django + React example project under `samples/` (#88).
- GitHub Actions workflows: `pr.yml` for linting and integration tests, `publish-package.yml` for tag-driven PyPI publishing.
- Docker Compose-based development workflow with streamlined linting and test scripts.

### Changed
- `InertiaRequest` now inherits from `HttpRequest` (#84), improving drop-in compatibility with Django middleware that type-checks `HttpRequest`.
- Replaced legacy CI workflows (`ci.yml`, `docs.yml`) with the fork-controlled `pr.yml` + `publish-package.yml`.
- Refreshed dependencies and project metadata in `pyproject.toml`.

### Removed
- Python 3.9 support (#86).
