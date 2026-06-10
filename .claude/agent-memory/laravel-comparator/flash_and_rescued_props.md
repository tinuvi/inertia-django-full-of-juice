---
name: flash-and-rescued-props
description: Laravel 3.x emits two page-object fields Django lacks — `flash` (one-shot session flash, reflashed across redirects) and `rescuedProps` (dot-paths whose Rescuable resolver threw; prop dropped, null returned, exception report()ed)
metadata:
  type: project
---

Two v3 page-object fields confirmed in `inertiajs/inertia-laravel` 3.x (line numbers verified 2026-06-09 at SHA `d51bac89fad1adae47a1b2eb44d2f31bff342ce4`, 2026-06-04) that the Django adapter (`inertia/http.py`) does not implement.

**Why:** Found during feature-parity sweeps vs the Django adapter. Both are real wire fields (test-confirmed), not framework-internal idioms.

**How to apply:** When asked about page-object fields, flash messaging, or exception rescue, mirror these facts:

### `flash`
- API: `ResponseFactory::flash()` L440-460 — string|array|BackedEnum|UnitEnum key; merges with existing via `session()->flash(SessionKey::FLASH_DATA, [...getFlashed(), ...$flash])` L454-457. Chainable `Response::flash()` L173-176 delegates to it.
- Session key: `Support/SessionKey.php` L15 `FLASH_DATA = 'inertia.flash_data'` (standard Laravel one-request flash).
- Read/pull: `getFlashed()` L477-482 (non-destructive get), `pullFlashed()` L489-494 (`session()->pull` = read+remove).
- Emission: `Response.php` toResponse L191-203 merges `resolveFlashData()` (L201); resolveFlashData L239-244 pulls and emits `['flash' => ...]` only when non-empty. Top-level page field, sibling of props; emitted on partials too (no partial gating).
- Redirect survival: `Middleware.php` L141-143 — any redirect response triggers `reflash()` L179-184, which re-flashes FLASH_DATA so it survives the POST -> 302/303 -> GET cycle; happens BEFORE the non-Inertia early return L145-147, so applies to non-Inertia redirects too. 303 conversion happens after (L157-159).
- Clearing: pull at render clears session; next request has no flash unless re-set.
- Companion: `Inertia::back()` L467-470 (Redirect::back wrapper).
- Django counterpart: MISSING. No flash() helper, no `flash` page field, no reflash in `inertia/middleware.py` (Django devs use django.contrib.messages; the middleware only marks messages storage unused on forced refresh).

### `rescuedProps`
- API: `ResponseFactory::defer(callable $callback, string $group = 'default', bool $rescue = false)` L246-249 — 3rd ctor arg ONLY; no `->rescue()` chainable (DeferProp.php L30-35, shouldRescue L50-53).
- Interface: `src/Rescuable.php` (`shouldRescue(): bool`). Only `DeferProp` implements it among built-ins (DeferProp.php L5), but `PropsResolver::resolveValue` checks `instanceof Rescuable` generically (L435), so custom props can opt in. Rescue is NOT available on optional/merge/always/once/scroll built-ins.
- Catch: `PropsResolver.php` resolveValue L429-472 — try L437-460; catch Throwable L461-471: rethrow if not rescuable, else `report($e)` L466, `$this->rescuedProps[] = $path` L468, return null L470.
- Prop is DROPPED from `props` (not null-valued): resolveProps L273-275 `if (in_array($path, $this->rescuedProps)) continue;`.
- Emission: buildMetadata L227-240 — `'rescuedProps' => $this->rescuedProps` (L236), array_filter keeps non-empty. Shape: flat array of dot-paths, e.g. `['stats']`, `['auth.notifications']` (tests/PropsResolverTest.php).
- Django counterpart: MISSING. `inertia/utils.py` `defer()` has no rescue param; no Rescuable concept; a throwing deferred resolver 500s.
