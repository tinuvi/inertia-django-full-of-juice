---
name: validation-errors
description: Laravel 3.x resolveValidationErrors (Middleware.php L223-247) vs Django _resolve_session_errors (http.py L351-381) — NOW MIRRORED (pull, first-message flatten, header nesting, always-included); residual gaps are named server bags + two corner-case timings.
metadata:
  type: project
---

Laravel 3.x validation-error handling vs Django adapter. Re-verified 2026-06-10 (3.x content identical to `d51bac8`). The 2026-05-30 claim "Django MISSING auto session injection" is OBSOLETE — the adapter gained `flash_errors` + `_resolve_session_errors` since.

**Laravel (inertia-laravel 3.x, src/Middleware.php):**
- L32 `protected $withAllErrors = false;` (no setter; subclass to flip — arrays instead of first message).
- L68-73 `share()` → `['errors' => Inertia::always($this->resolveValidationErrors($request))]`; registered EAGERLY at handle() L116, BEFORE `$next` (L138). AlwaysProp → survives partial reloads.
- L223-247 `resolveValidationErrors()`:
  - L225-227: no session or no `errors` key → `(object) []` (wire `{}`), header ignored.
  - L230: `session()->get('errors')->getBags()` — NON-destructive read of framework ViewErrorBag (flash aging removes it after the request).
  - L232-235: per bag, per field: `$this->withAllErrors ? $errors : $errors[0]` (first message).
  - L237-239: `default` bag exists AND request has `X-Inertia-Error-Bag` → `[header => default-bag]`. NOTE: any coexisting named bags are silently DROPPED.
  - L241-243: `default` exists, no header → flat default bag (named bags dropped here too).
  - L245: NO default bag → all named bags keyed by name, header ignored. ("named bags → keyed by name" requires *absence of default*, not mere presence of named bags.)
- Nesting depends ONLY on the CURRENT GET's header. Works after POST→302 because the browser's XHR/fetch transparently re-sends custom headers (incl. `X-Inertia-Error-Bag`, set per-visit at `inertiajs/inertia` `packages/core/src/requestParams.ts`) on same-origin redirect follow; the client does no manual redirect handling. Header absent (hard refresh / location flow) → flat.
- Storage half is FRAMEWORK: `withErrors()` flashes ViewErrorBag; consecutive `withErrors` on the same bag REPLACES that bag (`ViewErrorBag::put`).

**Django counterpart (inertia/http.py):**
- L43 `ALWAYS_INCLUDED_KEYS = frozenset({"errors"})`; build_props L246-254 merges `_resolve_session_errors()` only when the view/share didn't provide `errors` (props win — same precedence as Laravel); L270-278 keeps always-included keys on partials (partial-except may drop).
- L351-381 `_resolve_session_errors()`: `session.pop(INERTIA_SESSION_ERRORS)` (destructive + stash `_pulled_errors` for the 409 restore, see [[version-change-reflash]]); first message per field (L369-374); `{bag: flat} if bag else flat` (L375-381) using `error_bag()` L92-93. Empty store → `{}` un-nested. MIRRORS Laravel (a)+(b); (c) N/A (single default-bag store, no named bags).
- `flash_errors()` (storage half, mirrors `withErrors`): normalizes Form/dict → `{field: [str]}`; since 7475a91 (2026-06-10) it REPLACES the bag (`request.session[INERTIA_SESSION_ERRORS] = normalized`, ~L877) — matching `RedirectResponse::withErrors` (framework 13.x, RedirectResponse.php L132-147) → `ViewErrorBag::put` (ViewErrorBag.php L60-65, `$this->bags[$key] = $bag` = wholesale replace per named bag). `_normalize_errors` routes odd values through `ValidationError(value).messages` (Django idiom; spiritual analog = `MessageBag::__construct` L33-40 `(array) $value`) and drops empty lists at store time (MessageBag does NOT drop empties, but Laravel's Validator never stores them and Middleware L232-235 `$errors[0]` presumes non-empty — equivalent in practice).
- `redirect_back(request, *, errors=None, fallback="/")` (renamed from `back` in 7475a91): mirrors `Inertia::back(int $status = 302, array $headers = [], mixed $fallback = false)` (ResponseFactory.php L467-470 → `Redirect::back` → `UrlGenerator::previous` L162-175: raw referrer → session `_previous.url` → `to($fallback)` → `/`). Intentional divergences (documented CHANGELOG/README): validated referer (`url_has_allowed_host_and_scheme`), `resolve_url(fallback)` accepts URL names (Laravel's `to()` doesn't), no `$status`/`$headers` params (middleware 303 upgrade covers it), no session previous-URL chain.

**Residual deltas (all non-wire or exotic):**
1. Named server bags (validateWithBag) — Django has no authoring API; the header path produces the identical `{bag: {field: msg}}` wire shape, so no protocol divergence for flows Django supports.
2. CLOSED 2026-06-10 (was: Django merged field-wise across two failed POSTs) — `flash_errors` now replaces, matching `withErrors`.
3. Resolution timing: Laravel eager (pre-controller, handle L116) vs Django at render — differs only when one request both flashes errors and renders without redirecting (Django shows immediately; Laravel one render later). Canonical POST→redirect→GET identical.
4. No `withAllErrors` knob in Django (always first-message; non-list values pass through).
- `errors_response()` (422 JSON helper) remains a separate, manual mechanism — not this flow.
