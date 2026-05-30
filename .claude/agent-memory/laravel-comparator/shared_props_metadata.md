---
name: shared-props-metadata
description: Laravel 3.x emits a `sharedProps` page-object field (top-level Inertia::share keys), default ON; Django adapter has no equivalent
metadata:
  type: project
---

Laravel 3.x adds a `sharedProps` key to the page object: an array of the top-level prop keys that were registered via `Inertia::share`. Frontend uses it to carry shared props over during instant/prefetch visits.

**Why:** Found during a test-coverage gap analysis of the Django adapter vs `inertiajs/inertia-laravel` 3.x. This is a v3 page-object metadata field the Django adapter (`inertia/http.py`) does not implement at all.

**How to apply:** When asked about page-object fields or `sharedProps`, mirror these facts (branch `3.x`, SHAs in MEMORY.md):

- Emission gate: `src/PropsResolver.php` `resolveSharedProps()` (~L171). Reads `config('inertia.expose_shared_prop_keys', true)` — **default is TRUE**, so `sharedProps` is emitted on every response in a fresh install. When the config is false it is omitted.
- Field assembly: `src/PropsResolver.php` `buildMetadata()` returns `array_filter(['sharedProps' => $this->sharedPropKeys, 'mergeProps' => ..., ...])`. `array_filter` drops it when the key list is empty (so a response with no shared props omits it).
- Key derivation: for each resolved shared key, takes the segment before the first `.` (so `deep.foo.bar` shared key contributes `deep`), then `array_unique` + `array_values`.
- Config surface: `config/inertia.php` `'expose_shared_prop_keys' => true` (~L106, file last-modified 2026-04-08). Block titled "Expose Shared Prop Keys".
- Tests: `tests/HistoryTest.php::test_the_history_can_be_cleared_when_redirecting` asserts rendered shell JSON contains `"sharedProps":["errors"]`. `tests/ControllerTest.php` and `tests/ResponseFactoryTest.php` both assert `'sharedProps' => ['errors']`. `ResponseFactoryTest` also has a case asserting `assertArrayNotHasKey('sharedProps', ...)` — that path runs with the gate disabled.

Django counterpart: MISSING. `inertia/http.py` `page_data()` (L156-211) assembles component/props/url/version + conditional encryptHistory/clearHistory/preserveFragment/deferredProps/merge-kinds/onceProps/scrollProps. There is no `sharedProps`. `inertia/share.py` stores shared data on the request but never surfaces the key list into the page object. The `errors` auto-inject means a Django adapter mirroring this would emit at least `["errors"]` by default.
