# laravel-comparator memory

Index of confirmed mirrors, intentional divergences, and not-applicable Laravel patterns
between `inertiajs/inertia-laravel` (branch `3.x`) and this Django adapter.

## Last-checked Laravel SHA / dates
- `3.x` files read 2026-05-30. File last-modified stamps observed: `HttpGateway.php` 2026-04-08, `Middleware.php` 2026-03-11, `ResponseFactory.php` 2026-04-30, `ExcludesSsrPaths.php` 2026-02-09, `config/inertia.php` 2026-04-08, `PropsResolver.php` 2026-04-30, `tests/ResponseTest.php` 2026-03-11, `tests/MiddlewareTest.php`/`HistoryTest.php` 2026-02-24/25. Laravel framework `ExcludesPaths` trait read from `laravel/framework@12.x`.

## Comparisons
- [SSR route exclusion](ssr_route_exclusion.md) — Laravel withoutSsr/middleware-except/HttpGateway vs Django http.py; Django MISSING per-path exclusion.
- [sharedProps page-object field](shared_props_metadata.md) — Laravel emits `sharedProps` (Inertia::share key list), default ON; Django MISSING entirely.
- [Test coverage map](test_coverage_map.md) — Laravel 3.x test files → Django tests; gaps + not-applicable patterns from the 2026-05-30 analysis.
- [Asset version handling](asset_version_handling.md) — Laravel getVersion() (string) cast at ResponseFactory:150-154 + stale check Middleware:148; Django raw value = DIVERGENT bug on numeric INERTIA_VERSION.
