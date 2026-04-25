# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-25

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
