---
name: flash-and-rescued-props
description: Laravel 3.x emits two page-object fields Django lacks — `flash` (one-shot flash data, reflashed across redirects) and `rescuedProps` (paths whose deferred/rescuable resolver threw and was rescued to null)
metadata:
  type: project
---

Two v3 page-object fields confirmed present in `inertiajs/inertia-laravel` branch `3.x` (read 2026-05-31) that the Django adapter (`inertia/http.py`) does not implement.

**Why:** Found during a full feature-parity sweep vs the Django adapter. Both are real wire fields (test-confirmed), not framework-internal idioms.

**How to apply:** When asked about page-object fields, flash messaging, or error/exception rescue, mirror these facts:

### `flash`
- Producer: `src/ResponseFactory.php` `flash()` writes `session()->flash(SessionKey::FLASH_DATA, [...existing, ...new])`. `getFlashed()`/`pullFlashed()` read/pull it. `Response.php` `resolveFlashData()` (toResponse) emits `['flash' => $flash]` only when non-empty.
- Survives redirects: `src/Middleware.php` `reflash()` re-flashes `SessionKey::FLASH_DATA` on any redirect response so flash data survives the redirect→follow cycle.
- API: `Inertia::flash($key, $value)` (also array form, BackedEnum/UnitEnum keys), and `Response::flash()` chainable.
- Tests: `tests/ResponseFactoryTest.php` asserts `'flash' => ['message' => 'User updated!']` present, and `assertJsonMissing(['flash'])` when none. `tests/MiddlewareTest.php` shows a `share(['flash' => ...])` interplay.
- Django counterpart: MISSING. No `flash()` helper, no `flash` page field, no reflash-of-flash-data in `inertia/middleware.py`. Note: Django devs typically use `django.contrib.messages`; the Django middleware only touches `messages.get_messages` to mark storage unused on a forced refresh — it does not surface a `flash` page field.

### `rescuedProps`
- Producer: `src/PropsResolver.php` `resolveValue()` catch block — when a `Rescuable` prop (`$value->shouldRescue()` true) throws, it `report($e)`, pushes path to `$this->rescuedProps`, returns null. `buildMetadata()` emits `rescuedProps` when non-empty.
- Trigger API: `Inertia::defer($cb, $group, $rescue = true)` (the 3rd arg), or any `Rescuable` prop. So a deferred prop that throws on resolution is dropped from `props` and its dot-path listed in `rescuedProps` instead of 500-ing.
- Tests: `tests/PropsResolverTest.php` asserts `$page['rescuedProps'] === ['stats']` and `['auth.notifications']` with the prop removed from `props`.
- Django counterpart: MISSING. `inertia/utils.py` `defer(prop, group, merge, *, match_on)` has NO `rescue` parameter; there is no Rescuable concept and no `rescuedProps` page field. A throwing deferred resolver in Django will propagate (500), not be rescued.
