---
name: validation-errors
description: Laravel 3.x errors-prop / error-bag auto-injection (Middleware resolveValidationErrors) vs Django adapter; Django has NO automatic session->errors flashing but DOES reserve the errors key.
metadata:
  type: project
---

Laravel 3.x validation-error handling vs Django adapter. Read 2026-05-30.

**Laravel (inertia-laravel 3.x):**
- `src/Middleware.php:68-73` `share()` returns `['errors' => Inertia::always($this->resolveValidationErrors($request))]`. Wrapped in `always()` so the errors prop survives partial reloads. This is the ONLY default shared prop.
- `src/Middleware.php:223-247` `resolveValidationErrors()`:
  - L225-227: if no session or session lacks `errors`, return empty `(object) []`.
  - L230: `$bags = $request->session()->get('errors')->getBags();` — reads Laravel's `ViewErrorBag`.
  - L232-235: map each bag's `messages()`; per field take `$errors[0]` (first message) unless `$this->withAllErrors` (property, default false at L32; no setter — apps subclass middleware to flip it, see `WithAllErrorsMiddleware` test fixture).
  - L236-246 `pipe()`: if a `default` bag exists AND `X-Inertia-Error-Bag` header present -> `[header => default-bag]`; elif `default` bag exists -> return default bag flat (`{field: msg}`); else return all named bags keyed by bag name (`{bagName: {field: msg}}`).
- `src/Support/Header.php:15` `ERROR_BAG = 'X-Inertia-Error-Bag'`.
- Redirect-back flashing is FRAMEWORK, not inertia-laravel: `withErrors()` + `StartSession` flash `errors` (ViewErrorBag) to session; picked up next GET. inertia-laravel only READS the session bag.
- Tests `tests/MiddlewareTest.php:153-262` document exact shapes (default first-string, withAllErrors arrays, named-bag nesting, header scoping).

**Django counterpart (inertia/http.py):**
- `ALWAYS_INCLUDED_KEYS = frozenset({"errors"})` at L36; `build_props` does `_props.setdefault("errors", {})` at L216; partial filter keeps `errors` always (L232-240) unless in partial-except. So Django RESERVES the `errors` key and makes it always-included (mirrors Laravel's `always()` wrapper).
- DIVERGENT/MISSING: no `resolveValidationErrors` equivalent. Django never auto-reads a session error store, has no ViewErrorBag/MessageBag, no first-message flattening, no `X-Inertia-Error-Bag` scoping, no named bags. `errors` defaults to `{}` and is only populated if the user puts it there via `share()`/props.
- `errors_response()` at L626-640 is a helper returning `JsonResponse({"message","errors"}, status=422)` — a 422 JSON body, NOT the inertia errors-prop flow. Different mechanism (manual, opt-in).

**Recommendation:** Divergence is intentional and documented by the repo (error handling left to user). The errors-prop reservation IS mirrored (always-included key). The missing piece vs Laravel is automatic session->errors injection + error-bag header scoping (`Middleware.php:223-247`).
