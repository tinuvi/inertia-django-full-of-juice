---
name: precognition-ownership
description: Precognition lives 100% in laravel/framework — inertia-laravel 3.x has zero precognition code (verified by full-tree grep at SHA d51bac8)
metadata:
  type: project
---

Precognition is owned entirely by `laravel/framework`; `inertiajs/inertia-laravel` 3.x contains **no** precognition handling.

**Why:** Verified 2026-06-09 by `grep -rin precognit` over the full `3.x` tarball at SHA `d51bac89fad1adae47a1b2eb44d2f31bff342ce4` (2026-06-04) — zero matches. The Inertia v3 client talks straight to framework middleware; the adapter adds nothing.

**How to apply:** When asked where to mirror precognition for Django, cite laravel/framework (branch `13.x`, fetched 2026-06-09), not inertia-laravel:

- `src/Illuminate/Foundation/Http/Middleware/HandlePrecognitiveRequests.php` — handle L37-56 (header gate L39, `Precognition: true` resp header L50), prepareForPrecognition L64-70 (attribute `precognitive` L66, dispatcher rebind L68-69), appendVaryHeader L79-85 (`Vary: Precognition` on ALL responses, even non-precognitive), restoreDispatchers L94-104. Opt-in per route via alias `precognitive` (Foundation/Configuration/Middleware.php L813).
- `src/Illuminate/Http/Concerns/CanBePrecognitive.php` (trait on Request, Request.php L31) — filterPrecognitiveRules L15-26 (`Precognition-Validate-Only` comma list), shouldValidatePrecognitiveAttribute L35-46 (`*` wildcard -> `[^.]+` regex), isAttemptingPrecognition L53-56 (`Precognition: 'true'` header), isPrecognitive L63-66 (request attribute).
- `src/Illuminate/Foundation/Precognition.php` afterValidationHook L13-20 — abort 204 + `Precognition-Success: true` when validator clean AND Validate-Only header present.
- `src/Illuminate/Foundation/Routing/PrecognitionCallableDispatcher.php` L17-22 / `PrecognitionControllerDispatcher.php` L19-26 — resolve route/controller params (triggers FormRequest validation), then abort 204 `Precognition-Success: true`; controller body NEVER runs. ControllerDispatcher also ensureMethodExists L37-46 (RuntimeException).
- Rule filtering hooks: FormRequest.php createDefaultValidator L170-188 (filter at L181-185; `stopOnFirstFailure` L179 is the request's own property — precognition does NOT alter it); ValidatesWhenResolvedTrait.php L27-29 (after-hook only); ValidatesRequests.php validateWith L29-33 + validate L57-60; FoundationServiceProvider.php Request::validate macro L150-158.
- `precognitive()` helper: Foundation/helpers.php L656-684 — runs the closure, then abort 204 `Precognition-Success` for precognitive requests.
- Failure: ValidationException -> Handler.php invalidJson L836-842 = `$exception->status` (422) JSON `{message, errors}`; middleware tap still adds `Precognition: true` + Vary.
- Success shape: 204 no body + `Precognition: true` + `Precognition-Success: true` + `Vary: Precognition`.

Django adapter has no precognition surface at all (no header handling in inertia/middleware.py or inertia/http.py as of 2026-06-09).
