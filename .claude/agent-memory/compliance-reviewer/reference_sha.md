---
name: reference-sha
description: Laravel/framework/client reference points last compared against, with dates
metadata:
  type: reference
---

Canonical Laravel adapter compared against: `inertiajs/inertia-laravel`, branch `3.x`.

## Issue #5 advisory (2026-07-16) — 409 version-echo sources
- `inertia-laravel@3.x src/Middleware.php` (post-`022d54f`, PR #884 merged 2026-07-02T12:45Z): stale check L149 `header(Header::VERSION,'') !== getVersion()`; `onVersionChange()` ~L207-218 rebinds to `Inertia::location($request->fullUrl())` + `headers->set(Header::VERSION, Inertia::getVersion())` unconditionally; Vary set only on the discarded downstream response → the 409 carries NO Vary.
- `src/ResponseFactory.php`: `getVersion()` L154 `(string) $version` (null → `""`); `location()` L388-395 sets only `Header::LOCATION`.
- `tests/MiddlewareTest.php` L124-137: 409 asserts `X-Inertia-Location`, `X-Inertia-Version` exact value `'1234'`, empty body.
- Client `inertia@3.x packages/core/src/response.ts` (post-`36a5438`, PR #3180 merged 2026-07-02T13:18Z; shipped @inertiajs/core 3.6.0, npm 2026-07-02T14:56Z; latest 3.6.1): `isLocationVisit()` L197-199 = 409 + `x-inertia-location`; `locationVisit()` L204-236 — `versionChange = !!getHeader('x-inertia-version') && !== currentPage.version`, cancelable `fireLocationEvent(url, versionChange)` first, then `if (versionChange && async) return`.
- `packages/core/src/router.ts`: `async: true` at L165 (reload/poll/WhenVisible/deferred), L385 + L664 (prefetch).
- Spec `/docs/v3/core-concepts/the-protocol.md`: response-header table = X-Inertia, X-Inertia-Location, X-Inertia-Redirect, Vary, Precognition, Precognition-Success — version is request-side only; 409 example shows only X-Inertia-Location. `/docs/v3/advanced/asset-versioning.md` documents the v3.6.0+ background-request suppression behavior but NOT the echo mechanism.

## 0.5.0 review (2026-06-10) — flash/errors/precognition/rescued/shared sources
- `inertia-laravel@3.x src/Middleware.php` (full read): handle() order = `$next` → Vary → redirect-reflash (`reflash()`: `Inertia::getFlashed` non-destructive + re-flash FLASH_DATA) → non-Inertia early return → GET+version-mismatch → `onVersionChange` (`$session->reflash()` + `Inertia::location`) → empty→back → 302→303 → fragment→409. `resolveValidationErrors`: first message per field (`$errors[0]`, `$withAllErrors` opt-out), pipe = has('default')+header → `[header => default]`; has('default') → flat; else all bags keyed.
- `src/Response.php`: `toResponse` merges `resolveFlashData` (= `Inertia::pullFlashed`, emit `['flash'=>...]` only non-empty); `resolveClearHistory`/`resolvePreserveFragment` read Response properties.
- `src/ResponseFactory.php::flash`: `session()->flash(FLASH_DATA, [...getFlashed(), ...$flash])` — new wins. `back(int $status = 302, ...)` = Redirect::back wrapper.
- `src/PropsResolver.php` (full read): `resolve` = resolveSharedProps (gate `expose_shared_prop_keys` default true; first dot segment via strstr; array_unique) merged before props; `resolveProps` — `resolveValue` (catch Throwable → rethrow unless Rescuable→shouldRescue → report → `rescuedProps[] = $path` → null) then **`if in_array(path, rescuedProps) continue;` BEFORE `collectMetadata`** ⇒ rescued paths contribute NO merge metadata; `buildMetadata` array_filter count>0 keys: sharedProps/mergeProps/prependProps/deepMergeProps/matchPropsOn/deferredProps/rescuedProps/scrollProps/onceProps.
- `laravel/framework@13.x`: `HandlePrecognitiveRequests.php` (gate `isAttemptingPrecognition`; tap adds `Precognition: true` to whatever response; `appendVaryHeader` on ALL); `CanBePrecognitive.php` (explode ',' no trim; regex `'/^'.str_replace('\*','[^.]+',preg_quote($p)).'$/'`; `=== 'true'`); `Foundation/Precognition.php` (abort 204 + Precognition-Success only when messages empty AND Validate-Only present); both Precognition dispatchers `abort(204, ['Precognition-Success'=>'true'])` — so valid + NO Validate-Only also 204+Success; `Illuminate/Http/Request::json` L455-475 coerces malformed JSON to `[]` ⇒ malformed precognitive body = 422 required-errors in Laravel, never 400/500.
- Client `inertiajs/inertia@3.x packages/core`: `types.ts` Page L226-255 (`rescuedProps: string[]`, `sharedProps?: string[]`, `flash: FlashData`); `response.ts` `mergeProps()` body — a mergeProps path absent from incoming props is a NO-OP (`get()` undefined → neither Array nor object branch).
- Spec `/v3/core-concepts/the-protocol.mdx`: Precognition-Validate-Only L151, Precognition-Success L181, rescuedProps L256+L319-331, sharedProps L262, 409 flash-reflash obligation L480/495. `instant-visits.mdx` L180-186: disabling the gate omits only the metadata key.

## Prior (0.4.0, 2026-05-30) — SSR exclusion sources
- `src/Ssr/HttpGateway.php` — `dispatch()` returns `null` when `ssrIsEnabled()` is false; `ssrIsEnabled()` = `$enabled && ! $this->inExceptArray($request)`. The gateway uses the `ExcludesPaths` trait; `withoutSsr` populates `$except` via `except()`.
- `Illuminate\Foundation\Http\Middleware\Concerns\ExcludesPaths::inExceptArray` (laravel/framework) — `trim($except,'/')` then `fullUrlIs || is`; `Str::is` glob, whole-string anchored.
- When SSR is excluded, observable wire result == client-side-only shell, no POST to SSR server.

See [[divergence-ssr-exclude-regex-vs-glob]] and [[divergence-v3-completion-accepted]].
