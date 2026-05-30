# laravel-comparator memory

Index of confirmed mirrors, intentional divergences, and not-applicable Laravel patterns
between `inertiajs/inertia-laravel` (branch `3.x`) and this Django adapter.

## Last-checked Laravel SHA / dates
- `3.x` files read 2026-05-30. File last-modified stamps observed: `HttpGateway.php` 2026-04-08, `Middleware.php` 2026-03-11, `ResponseFactory.php` 2026-04-30, `ExcludesSsrPaths.php` 2026-02-09. Laravel framework `ExcludesPaths` trait read from `laravel/framework@12.x`.

## Comparisons
- [SSR route exclusion](ssr_route_exclusion.md) — Laravel withoutSsr/middleware-except/HttpGateway vs Django http.py; Django MISSING per-path exclusion.
