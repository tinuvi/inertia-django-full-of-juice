# laravel-comparator memory

Index of confirmed mirrors, intentional divergences, and not-applicable Laravel patterns
between `inertiajs/inertia-laravel` (branch `3.x`) and this Django adapter.

## Last-checked Laravel SHA / dates
- Full parity sweep 2026-05-31. `3.x` last-modified stamps: `Response.php` 2026-04-09, `ResponseFactory.php`/`PropsResolver.php` 2026-04-30, `Middleware.php` 2026-03-11, `Middleware/EnsureGetOnRedirect.php` 2026-04-09, `Support/Header.php` 2026-02-24, `ScrollProp.php` 2026-03-11, `OnceProp.php` 2025-12-15, `ResolvesOnce.php` 2025-12-10, `config/inertia.php` 2026-04-08. `src/` now has `flash`/`shareOnce`/`transformComponentUsing`/`resolveUrlUsing`/`back`/`rescuedProps` surface. Testing helpers: `AssertableInertia.php`, `ReloadRequest.php`, `TestResponseMacros.php`.
- Prior: `3.x` files read 2026-05-30. Laravel framework `ExcludesPaths` trait read from `laravel/framework@12.x`.

## Comparisons
- [SSR route exclusion](ssr_route_exclusion.md) — Laravel withoutSsr/middleware-except/HttpGateway vs Django http.py; Django MISSING per-path exclusion.
- [sharedProps page-object field](shared_props_metadata.md) — Laravel emits `sharedProps` (Inertia::share key list), default ON; Django MISSING entirely.
- [Test coverage map](test_coverage_map.md) — Laravel 3.x test files → Django tests; gaps + not-applicable patterns from the 2026-05-30 analysis.
- [Asset version handling](asset_version_handling.md) — Laravel getVersion() (string) cast at ResponseFactory:150-154 + stale check Middleware:148; Django raw value = DIVERGENT bug on numeric INERTIA_VERSION.
- [Validation errors / error bags](validation_errors.md) — Laravel Middleware:68-73,223-247 auto-injects errors prop from session ViewErrorBag + X-Inertia-Error-Bag scoping; Django reserves errors key (always-included) but MISSING auto session injection (intentional).
- [flash + rescuedProps page fields](flash_and_rescued_props.md) — Laravel emits `flash` (one-shot, reflashed on redirect) and `rescuedProps` (defer rescue=true); Django MISSING both.
