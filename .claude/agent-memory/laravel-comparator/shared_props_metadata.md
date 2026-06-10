---
name: shared-props-metadata
description: Laravel 3.x emits a `sharedProps` page-object field (top-level Inertia::share keys), default ON via expose_shared_prop_keys; Django adapter has no equivalent
metadata:
  type: project
---

Laravel 3.x adds a `sharedProps` key to the page object: an array of the top-level prop keys registered via `Inertia::share`. Frontend uses it to carry shared props over during instant/prefetch visits (per config/inertia.php comment).

**Why:** Found during a test-coverage gap analysis of the Django adapter vs `inertiajs/inertia-laravel` 3.x. A v3 page-object metadata field the Django adapter (`inertia/http.py`) does not implement at all.

**How to apply:** When asked about page-object fields or `sharedProps`, mirror these facts (lines verified 2026-06-09 at SHA `d51bac89fad1adae47a1b2eb44d2f31bff342ce4`):

- Tracking: `ResponseFactory.php` L46 `$sharedProps = []`; `share()` L101-111 (array merge / Arrayable / dot-key via `Arr::set`); `getShared()` L122-128; `flushShared()` L136-138; `render()` passes `$this->sharedProps` into the Response ctor (L374). `Response.php` keeps them separate from page props (L89, ctor L97-107) until resolution.
- Resolution: `Response::toResponse` L188-189 -> `PropsResolver->resolve($shared, $props)`; `PropsResolver.php` resolve L161-168 merges resolved shared BEFORE page props (page props win collisions, L163).
- Emission gate: `resolveSharedProps()` L177-194 — reads `config('inertia.expose_shared_prop_keys', true)` at L181; **default TRUE**. When false, keys are not collected (field omitted).
- Key derivation L185-191: segment before first `.` (`strstr($key, '.', true)`), then `array_unique` + `array_values`. Top-level names only, not dot-paths.
- Field assembly: `buildMetadata()` L227-240 — `'sharedProps' => $this->sharedPropKeys` (L230), `array_filter(..., count > 0)` drops it when empty.
- Conditions: collected on EVERY resolve — initial loads, Inertia visits, AND partial reloads (resolve() runs resolveSharedProps before partial filtering in resolveProps). Keys appear even if the prop values were filtered out of `props` by only/except.
- In practice >= `['errors']`: `Middleware.php` share() L68-73 always shares `'errors' => Inertia::always(resolveValidationErrors($request))`, registered in handle() L116.
- Config block: `config/inertia.php` L122 `'expose_shared_prop_keys' => true`.
- Tests: `tests/HistoryTest.php` (shell JSON contains `"sharedProps":["errors"]`), `tests/ControllerTest.php`, `tests/ResponseFactoryTest.php` (incl. assertArrayNotHasKey when gate disabled).

Django counterpart: MISSING. `inertia/http.py` `page_data()` assembles component/props/url/version + conditional encryptHistory/clearHistory/preserveFragment/deferredProps/merge-kinds/onceProps/scrollProps — no `sharedProps`. `inertia/share.py` never surfaces the key list. A Django mirror would emit at least `["errors"]` by default given errors auto-share.
