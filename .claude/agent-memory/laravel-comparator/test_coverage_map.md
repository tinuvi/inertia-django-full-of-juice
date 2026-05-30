---
name: test-coverage-map
description: Mapping of Laravel 3.x test files/behaviors to Django adapter tests; records gaps found in the 2026-05-30 coverage analysis
metadata:
  type: project
---

Test-suite parity map between `inertiajs/inertia-laravel` 3.x (`tests/`) and the Django adapter (`inertia/tests/` + `playwright_e2e/`). Built 2026-05-30.

**Why:** User asked for a coverage gap report — which Laravel-tested protocol behaviors we don't test or don't implement.

**How to apply:** Use as the starting index when re-running coverage comparisons; re-verify against live code before acting (memory is a snapshot).

Laravel test files (branch 3.x): AlwaysPropTest, ComponentTest, ControllerTest, DeepMergePropTest, DeferPropTest, DirectiveTest, ExceptionResponseTest, HelperTest, HistoryTest, HttpGatewayTest, MergePropTest, MiddlewareTest, OncePropTest, OptionalPropTest, PropsResolverTest, ResponseFactoryTest, ResponseTest, ScrollMetadataTest, ScrollPropTest, ServiceProviderTest, SsrRenderFailedTest, Testing/* , Commands/* , Enums/*.

Genuine protocol gaps found (Laravel tests it, Django does not):
- **sharedProps page-object field** — MISSING in Django. See [[shared-props-metadata]]. Default ON in Laravel.
- **Nested/dot-path partial filtering** — Laravel `ResponseTest::test_nested_partial_props`, `test_exclude_nested_props_from_partial_response` exercise `X-Inertia-Partial-Data: auth.user` and `X-Inertia-Partial-Except: auth.user` (dot-path into nested props). Django `build_props` only does flat top-level key matching (`inertia/http.py` L232-291). Likely a real gap.
- **Top-level dot-prop unpacking** — Laravel `ResponseTest::test_top_level_dot_props_get_unpacked` / `test_nested_dot_props_do_not_get_unpacked`: a top-level key like `auth.user.can` is expanded into nested structure; nested dot keys are not. Django has no unpack step. Real gap.
- **String callables not invoked** — Laravel `test_string_function_names_are_not_invoked_as_callables`: a prop value of the string `'date'`/`'trim'` must NOT be called even though it is a PHP-callable string. Django uses `callable()` on Python objects; a plain str is not callable, so behavior likely already matches — but untested. Minor.
- **Version mismatch only forces reload on the value, version optional/number/string** — Laravel MiddlewareTest covers version optional + numeric + string + 409 mismatch. Django test_middleware covers 409 mismatch + a string version (test_settings). Numeric-version and "version optional" cases untested but behavior is identical (string compare). Minor.

Laravel behaviors that are framework-specific / NOT applicable to Django (skip, not gaps):
- Validation-error sharing from session ViewErrorBag, named error bags, `X-Inertia-Error-Bag` scoping (MiddlewareTest) — Laravel session/validation machinery; Django uses `errors_response` + `share(errors=...)`.
- Asset version from app.asset_url / Vite / Mix manifest hash (MiddlewareTest) — Django uses static `INERTIA_VERSION`.
- `handleExceptionsUsing` / ExceptionResponse rendering Inertia error pages (ExceptionResponseTest) — Laravel exception-handler hook; Django has no equivalent surface and errors_response covers the 422 case only.
- ProvidesInertiaProperties / Responsable / Arrayable / Promise / Eloquent resource prop resolution (ResponseTest) — PHP type-system specific.
- ScrollMetadata::fromPaginator (ScrollMetadataTest) — Django infinite_scroll deliberately does NOT couple to Paginator; caller passes metadata. Intentional divergence, documented in infinite_scroll.py docstring.
- Blade @inertia / @inertiaHead directives (DirectiveTest) — Blade-only.
- shareOnce middleware merge (MiddlewareTest) — Laravel middleware API; Django share() is a function.
- flash data preservation on redirect, redirect()->preserveFragment macro (HistoryTest/MiddlewareTest) — Laravel redirect macro; Django uses preserve_fragment(request) session flash, already tested.

Intentional divergences (out of scope, not gaps):
- INERTIA_SSR_EXCLUDE regex-vs-glob — see [[ssr-route-exclusion]].
- infinite_scroll metadata is caller-supplied, not Paginator-derived.
