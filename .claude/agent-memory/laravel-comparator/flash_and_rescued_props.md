---
name: flash-and-rescued-props
description: Laravel 3.x `flash` and `rescuedProps` page-object fields — BOTH NOW MIRRORED in Django (http.py flash()/build_flash, _rescued_props) as of the 2026-06 feature-matrix work; Laravel mechanics below stay authoritative.
metadata:
  type: project
---

Two v3 page-object fields confirmed in `inertiajs/inertia-laravel` 3.x (line numbers verified 2026-06-09 at SHA `d51bac89fad1adae47a1b2eb44d2f31bff342ce4`, 2026-06-04). STATUS CHANGE 2026-06-10: the Django adapter NOW IMPLEMENTS both (the "MISSING" notes below are corrected inline).

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
- Django counterpart: NOW MIRRORED (2026-06-10). `inertia/http.py` `flash()` L786-797 (merge semantics like ResponseFactory::flash), `build_flash()` L383-414 (pop = pull, stash `_pulled_flash` L400, optional `INERTIA_FLASH_FROM_MESSAGES` drain of django.contrib.messages into `flash.messages`); session key `_inertia_flash` (L35). 409 restore via `middleware.py` `reflash_one_shot_state` L114-161 — Django is MORE preserving than Laravel here, see [[version-change-reflash]] (Laravel's blanket reflash cannot restore the pulled value).

### `rescuedProps`
- API: `ResponseFactory::defer(callable $callback, string $group = 'default', bool $rescue = false)` L246-249 — 3rd ctor arg ONLY; no `->rescue()` chainable (DeferProp.php L30-35, shouldRescue L50-53).
- Interface: `src/Rescuable.php` (`shouldRescue(): bool`). Only `DeferProp` implements it among built-ins (DeferProp.php L5), but `PropsResolver::resolveValue` checks `instanceof Rescuable` generically (L435), so custom props can opt in. Rescue is NOT available on optional/merge/always/once/scroll built-ins.
- Catch: `PropsResolver.php` resolveValue L429-472 — try L437-460; catch Throwable L461-471: rethrow if not rescuable, else `report($e)` L466, `$this->rescuedProps[] = $path` L468, return null L470.
- Prop is DROPPED from `props` (not null-valued): resolveProps L273-275 `if (in_array($path, $this->rescuedProps)) continue;`.
- Emission: buildMetadata L227-240 — `'rescuedProps' => $this->rescuedProps` (L236), array_filter keeps non-empty. Shape: flat array of dot-paths, e.g. `['stats']`, `['auth.notifications']` (tests/PropsResolverTest.php).
- Django counterpart: NOW MIRRORED (2026-06-10). `inertia/http.py` L340-347: throwing resolver → `logger.exception` (mirror of `report()`), `del _props[key]` (prop dropped), `self._rescued_props.append(key)` → emitted as the `rescuedProps` page field.
