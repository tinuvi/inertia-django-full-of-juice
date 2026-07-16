---
name: version-header-on-409
description: Laravel 3.x echoes X-Inertia-Version on the stale-version 409 (Middleware.php:216, PR #884, shipped v3.1.1) so the 3.6+ client (PR #3180, shipped v3.6.0) can suppress hard reloads on async requests; Django gap confirmed twice (2026-07-16, incl. adversarial pass). Fix: force_refresh only, ALWAYS set, value = resolve_inertia_version().
metadata:
  type: project
---

Verified 2026-07-16 (initial sweep + same-day adversarial re-verification against live `3.x` HEAD with cache bypass).

## Laravel: the header exists since 2026-07-02, unconditionally

`src/Middleware.php` L207-219 `onVersionChange()` — L215-216:
```php
$response = Inertia::location($request->fullUrl());
$response->headers->set(Header::VERSION, Inertia::getVersion());
```
- **PR #884** `022d54f`, merged 2026-07-02T12:45Z, shipped in **inertia-laravel v3.1.1** (released 2026-07-02T14:50Z). Full diff = +4/-1 in `Middleware.php` + ONE assertion in the existing `tests/MiddlewareTest.php::test_it_will_instruct_inertia_to_reload_on_a_version_mismatch` (new L135: `assertHeader('X-Inertia-Version', '1234')`, next to the existing `assertHeader('X-Inertia-Location', $this->baseUrl)`). Nothing else — no session interplay, no new test cases, 0 review comments.
- No follow-ups/reverts: only commit touching `Middleware.php` since 2026-06-20 is `022d54f`; `ResponseFactory.php` untouched since 2026-04-30. No regression issues as of 2026-07-16 (inertia-laravel: only #886 previousUri, unrelated; inertia: #3187/#3191/#3195/#3199, none about location).
- The set is **unconditional** — no truthiness guard. `getVersion(): string` (`ResponseFactory.php` L154-161) returns `(string) $version` ⇒ `''` when unset. Reachable with `''`: client sends stale non-empty version after server disables versioning (L149: `$request->header(Header::VERSION, '') !== ''`) ⇒ wire = header present with EMPTY value. Client-invisible vs absent (`!!'' === !!undefined === false`; `hasHeader` never consulted for version). **Mirror = always set, even when `resolve_inertia_version() == ""`.** Skip-when-empty would be the divergence, not the mirror.

## Discriminator design confirmed from both PR bodies

- #884 body: 409 "was indistinguishable from a manual `Inertia::location()` redirect".
- #3180 body (`36a5438`, merged 2026-07-02T13:18Z, shipped **@inertiajs/core v3.6.0**, 2026-07-02T14:52Z): "a manual `Inertia::location()` (which carries no version header) always navigates"; documents the `location`-event banner pattern keyed on `event.detail.versionChange`.
- `ResponseFactory::location()` L388-395 sets only `Header::LOCATION` — deliberately untouched by #884. Putting the header in generic `location()` would (1) swallow manual locations on async non-GET requests from version-stale clients (`versionChange && async` guard, `response.ts` L219-222) and (2) misfire userland versionChange banners on manual redirects even for sync visits. NOTE the GET caveat: both middlewares run the view first, then REPLACE stale-GET responses with the version-409 (Laravel `handle()` L138+L149; our `__call__` L64-71), so the swallow scenario needs a non-GET async request — real but narrower than "any async request".

## Client mechanics (v3.6.0+)

- `packages/core/src/response.ts` L204-231 `locationVisit`; `getHeader` = `this.response.headers[header]` (L186-188); hash restored client-side via `setHashIfSameUrl` (L152-154).
- Request side (`packages/core/src/request.ts`): `page.version && (headers['X-Inertia-Version'] = page.version)` — header OMITTED when page.version falsy.

## Django fix shape (issue #5 — verified as filed via gh, created 2026-07-16)

- Set `X-Inertia-Version: resolve_inertia_version()` in `force_refresh()` (`inertia/middleware.py:105-113`) ONLY; `location()` (`inertia/http.py:776-784`) stays version-free. Always set (no truthiness guard). Value = resolved CURRENT server version, never an echo of the request header.
- Test mirror: extend the existing stale-409 assertions with the header check, same response.
- Commit-body citation: `inertia-laravel 3.x src/Middleware.php:216 (PR #884, 022d54f, v3.1.1) + inertiajs/inertia packages/core/src/response.ts:209-222 (PR #3180, 36a5438, v3.6.0)`.

## Adjacent findings from the adversarial pass (out of scope for #5)

- **Stale-check default divergence**: Laravel L149 defaults the request header to `''` ⇒ Inertia GET WITHOUT `X-Inertia-Version` + configured server version ⇒ STALE ⇒ 409. Django `is_stale` defaults to `server_version` ⇒ absent header never stale (inherited from reference inertia-django). Django soft-heals via `page.version` in the next JSON page object; Laravel forces the asset reload. Real divergence, separate decision.
- **fullUrl() vs build_absolute_uri()**: both include the query string; Laravel's is NORMALIZED (Symfony `normalizeQueryString`: `ksort` + `http_build_query(..., PHP_QUERY_RFC3986)`, http-foundation `Request.php` L707-717; empty qs ⇒ no `?`) and `url()` rtrims trailing `/` (framework 12.x `Request.php` L130-133). Django preserves raw order/encoding AND the trailing slash — REQUIRED for Django (APPEND_SLASH); do not mirror the rtrim. Fragments: server-side never (not sent over HTTP).

## Other adapters (still behind, not a consensus against)

- inertia-rails `lib/inertia_rails/middleware.rb` L110-113 `force_refresh`: no version header. File touched 2026-07-15 but for unrelated sessionless-session work — not a considered rejection.
- Reference inertia-django `inertia/middleware.py` L57-62: no header (last touched 2025-10-05). Quirk: its `__call__` gates on `is_stale` WITHOUT the GET check (`is_stale_inertia_get` defined but unused there) — 409s stale non-GETs, diverging from Laravel L149; ours correctly gates on GET.

See [[version-change-reflash]] for the session-restore side of the same 409.
