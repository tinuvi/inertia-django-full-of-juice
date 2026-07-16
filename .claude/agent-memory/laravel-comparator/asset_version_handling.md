---
name: asset-version-handling
description: How inertia-laravel 3.x resolves/casts the asset version (getVersion(): string, ResponseFactory.php:154-160) — Django's former raw-value bug is FIXED by resolve_inertia_version() in settings.py; now MIRRORED.
metadata:
  type: project
---

Asset version handling comparison, scanned 2026-05-30 against `inertiajs/inertia-laravel@3.x`; **line numbers + Django verdict re-verified 2026-07-16**.

> **RESOLVED 2026-07-16:** the string-cast bug and the missing-callable feature described below are both FIXED. `inertia/settings.py:45-60` `resolve_inertia_version() -> str` invokes a callable `INERTIA_VERSION`, maps `None → ""`, and casts to `str` — an explicit mirror of `ResponseFactory::getVersion(): string` (cited in its own docstring). Call sites use it (`middleware.py:97`, `http.py`). Django is now **SAME**, not divergent. The "Verdict" line at the bottom is historical.

**How to apply:** When reviewing version emission or the stale check, this is settled — mirror confirmed. Live question is the *response* header on the 409, see [[version-header-on-409]].

## Laravel 3.x (resolved string everywhere)
- `ResponseFactory::version($version)` — setter stores raw value (closure/number/string), no validation.
- `ResponseFactory::getVersion(): string` — `src/ResponseFactory.php:154-160` (was :150-154 before 2026-04-30) — resolves closure via `App::call`, then `return (string) $version;`. Return type is declared `: string`. THIS is the single cast point.
- `Response` page object — `src/Response.php:191` — `'version' => $this->version`. NOT a raw cast here; `$this->version` on the Response was passed in by `ResponseFactory::render()` as `$this->getVersion()` (already a string). So emit is string by construction.
- Stale check — `src/Middleware.php:148` — `$request->method() === 'GET' && $request->header(Header::VERSION, '') !== Inertia::getVersion()`. Both operands are strings: header is always string; `getVersion()` casts. Default for missing header is `''` (empty string), not the configured version.
- `Middleware::version()` — `src/Middleware.php` — default resolver returns `hash('xxh128', ...)` of asset_url/manifest, or `null`. `(string) null === ''`, so null version round-trips to `''` and matches the missing-header default `''` → never stale. That is how `test_the_version_is_optional` passes.

## Laravel tests (tests/MiddlewareTest.php, lastModified 2026-02-24)
- `test_the_version_is_optional` (~L84) — no version set, GET with X-Inertia, asserts 200.
- `test_the_version_can_be_a_number` (~L93) — sets version to int `1597347897973`, sends matching `X-Inertia-Version` header, asserts 200 (no reload). Proves int round-trips via `(string)` cast.
- `test_the_version_can_be_a_string` (~L?) — version `'foo-version'`, asserts 200.
- `test_it_will_instruct_inertia_to_reload_on_a_version_mismatch` — version `'1234'`, header `'4321'`, asserts 409 + `X-Inertia-Location`.

## Django (divergent — bug), re-verified 2026-05-30 against live tree
- `INERTIA_VERSION` default — `inertia/settings.py:11` — `INERTIA_VERSION = "1.0"` static string attr; no callable support, no manifest hashing.
- `inertia/http.py:160` — `"version": settings.INERTIA_VERSION` — raw, no `str()`. Divergent from Laravel emit-as-string-by-construction.
- `inertia/middleware.py:88-92` `is_stale()` — compares `request.headers.get("X-Inertia-Version", settings.INERTIA_VERSION) != settings.INERTIA_VERSION` — raw both sides; missing-header default is INERTIA_VERSION (not Laravel's `''`).
- `inertia/middleware.py:94-95` `is_stale_inertia_get()` — gates on `request.method == "GET"`. Matches Laravel's `method()==='GET'` gate (Middleware.php:148).
- `inertia/http.py:589-597` `location()` — 409 + `X-Inertia-Location`. Mirrors Laravel `ResponseFactory::location()` (ResponseFactory.php ~L373: `BaseResponse::make('',409,[Header::LOCATION => ...])`).
- CORRECTION to prior note: the missing-header default divergence (`INERTIA_VERSION` vs `''`) is DEFENSIBLE, not the bug. Django treats absent header as not-stale (no reload), which is conservative/safe. The genuine bug is solely the missing `str()` cast: a non-string `INERTIA_VERSION` (e.g. int) emits a non-string into JSON and the stale compare is str-header vs non-str-setting → guaranteed mismatch → 409 reload loop on every GET.
- Verdict: DIVERGENT (one real gap = no string cast; one missing feature = no callable/closure version). To mirror cast, cite `ResponseFactory.php:150-154 (getVersion(): string { ... return (string) $version; })`. To mirror callable, cite same method (Closure → `App::call`) + `Middleware::version()` default manifest-hash resolver (`hash_file('xxh128', public_path('build/manifest.json'))`).
