---
name: asset-version-handling
description: How inertia-laravel 3.x resolves/casts the asset version (string cast) vs Django adapter's raw-value bug on numeric INERTIA_VERSION
metadata:
  type: project
---

Asset version handling comparison, scanned 2026-05-30 against `inertiajs/inertia-laravel@3.x`.

**Why:** Django adapter has a likely bug — non-string `INERTIA_VERSION` (e.g. int `42`) causes a 409 reload loop because HTTP headers are always strings and the stale check compares str vs int.

**How to apply:** When reviewing/fixing version emission or stale check, mirror Laravel's two-point string cast.

## Laravel 3.x (resolved string everywhere)
- `ResponseFactory::version($version)` — `src/ResponseFactory.php:148` — setter stores raw value (closure/number/string), no validation.
- `ResponseFactory::getVersion(): string` — `src/ResponseFactory.php:150-154` — resolves closure via `App::call`, then `return (string) $version;`. Return type is declared `: string`. THIS is the single cast point.
- `Response` page object — `src/Response.php:191` — `'version' => $this->version`. NOT a raw cast here; `$this->version` on the Response was passed in by `ResponseFactory::render()` as `$this->getVersion()` (already a string). So emit is string by construction.
- Stale check — `src/Middleware.php:148` — `$request->method() === 'GET' && $request->header(Header::VERSION, '') !== Inertia::getVersion()`. Both operands are strings: header is always string; `getVersion()` casts. Default for missing header is `''` (empty string), not the configured version.
- `Middleware::version()` — `src/Middleware.php` — default resolver returns `hash('xxh128', ...)` of asset_url/manifest, or `null`. `(string) null === ''`, so null version round-trips to `''` and matches the missing-header default `''` → never stale. That is how `test_the_version_is_optional` passes.

## Laravel tests (tests/MiddlewareTest.php, lastModified 2026-02-24)
- `test_the_version_is_optional` (~L84) — no version set, GET with X-Inertia, asserts 200.
- `test_the_version_can_be_a_number` (~L93) — sets version to int `1597347897973`, sends matching `X-Inertia-Version` header, asserts 200 (no reload). Proves int round-trips via `(string)` cast.
- `test_the_version_can_be_a_string` (~L?) — version `'foo-version'`, asserts 200.
- `test_it_will_instruct_inertia_to_reload_on_a_version_mismatch` — version `'1234'`, header `'4321'`, asserts 409 + `X-Inertia-Location`.

## Django (divergent — bug)
- `inertia/http.py:160` — `"version": settings.INERTIA_VERSION` — raw, no `str()`. Divergent from emit-as-string-by-construction.
- `inertia/middleware.py:88-92` `is_stale()` — compares `request.headers.get("X-Inertia-Version", settings.INERTIA_VERSION) != settings.INERTIA_VERSION` — raw both sides; also uses INERTIA_VERSION (not `''`) as the missing-header default, unlike Laravel's `''`.
- Verdict: DIVERGENT. To mirror, cast to string at both points; mirror citation = `ResponseFactory.php:150-154 (return (string) $version)` and `Middleware.php:148`.
