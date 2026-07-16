---
name: advisory-issue5-version-header-409
description: Pre-implementation advisory (2026-07-16) for issue #5 — echo X-Inertia-Version on the stale 409; would-PASS conditions, E2E client-version blocker, and adjacent out-of-scope divergences
metadata:
  type: project
---

Advisory verdict issued 2026-07-16 for tinuvi/inertia-django-full-of-juice#5 (no diff existed yet). Reuse these conditions verbatim when the implementation diff arrives; all citations were independently verified that day (see [[reference-sha]]).

## Would-PASS conditions (the checklist for the real review)

1. Header set in `InertiaMiddleware.force_refresh()` ONLY; `inertia/http.py::location()` stays version-free. Laravel: `Middleware.php` `onVersionChange()` sets it (PR #884, 022d54f); `ResponseFactory::location()` sets only `Header::LOCATION`.
2. Value = `resolve_inertia_version()`, set UNCONDITIONALLY — including `""` when `INERTIA_VERSION` is unset. Laravel emits the empty header too (`(string) $version`); the 3.x client treats `''` and absent identically (`!!responseVersion`). A non-empty guard would be a needless divergence.
3. Nothing else on the 409: no Vary (Laravel's rebound 409 never receives the Vary set on the discarded downstream response), empty body (`MiddlewareTest` asserts `assertEmpty`), status 409, `X-Inertia-Location` = full URL incl. query.
4. `inertia_redirect()` (X-Inertia-Redirect 409) stays version-free — matches `onRedirectWithFragment`.
5. Unit test pins the exact header VALUE (Laravel pins `'1234'`, `tests/MiddlewareTest.php:135`), not mere presence; also pin the empty-version edge (INERTIA_VERSION=None → header present and empty) to protect condition 2.
6. **E2E blocker**: `sample_project/package.json` pins `@inertiajs/core`+`react` `^3.3.1` < 3.6.0 — the poll-across-deploy suppression spec cannot pass until the sample client is bumped to >=3.6.0 (3.6.1 latest as of 2026-07-16). The bump is part of the fix's proof, not optional.

## Known fragile area

`location()` is the discriminator: version header present = automatic version-change 409 (client may suppress on async), absent = manual redirect (client always navigates). Pushing the header into `location()` breaks manual redirects for stale async non-GET visits (versionChange && async → client returns early, redirect never happens). Flag ANY future diff that adds headers to `location()`.

## Adjacent pre-existing divergences (observed, NOT part of issue #5, do not block)

- **Headerless Inertia GET staleness**: `is_stale` defaults the missing request header to `server_version` (never stale, `inertia/middleware.py:96-100`, pinned intentionally by `inertia/tests/test_middleware.py:50-56` comment); Laravel `$request->header(Header::VERSION, '') !== Inertia::getVersion()` 409s a headerless GET whenever a version is configured. Unreachable for the real client (it only omits the header when page.version was falsy). Accepted-by-test; don't re-flag without new evidence.
- **Check ordering**: our fragment-redirect 409 runs before the stale check; Laravel runs version-change first (`Middleware.php:149`). Stale GET + fragment redirect converges after one extra round trip. Unchanged by this fix.
- Double resolution of the version (stale check + header) matches Laravel calling `Inertia::getVersion()` twice — non-deterministic version callables behave identically in both.

**Why:** the adversarial pre-review confirmed issue #5 sound end-to-end; recording the conditions avoids re-deriving the whole chain (2 repos, 2 PRs, spec pages, npm timeline) at implementation time.
**How to apply:** when the diff lands, verify conditions 1-6 mechanically, re-check only that Laravel `3.x` Middleware.php has not moved again, and consult [[divergence-v3-completion-accepted]] for the reflash surface (its point 5 covers the stronger-than-Laravel 409 restore, unaffected here).
