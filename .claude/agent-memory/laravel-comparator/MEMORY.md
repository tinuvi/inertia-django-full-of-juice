# laravel-comparator memory

Index of confirmed mirrors, intentional divergences, and not-applicable Laravel patterns
between `inertiajs/inertia-laravel` (branch `3.x`) and this Django adapter.

## Last-checked Laravel SHA / dates
- 2026-06-10 (7475a91 review): framework 13.x — RedirectResponse::withErrors L132-147, ViewErrorBag::put L60-65, Request::json L462-466 (coerce-to-empty), MessageBag ctor L33-40, UrlGenerator::previous L162-175. 3.x — ResponseFactory::back L467-470, PropsResolver resolveProps L248 / rescued continue L273-275 / collectMetadata L490.
- 2026-06-10: `3.x` re-fetched; Middleware/Response/ResponseFactory/SessionKey content identical to `d51bac8` readings. Store::reflash cited from `laravel/framework@12.x` Store.php L503-508.
- 2026-06-09: `3.x` head = `d51bac89fad1adae47a1b2eb44d2f31bff342ce4` (2026-06-04). Flash/rescued/shared line numbers re-verified at this SHA; framework cites = `13.x`.
- Full parity sweep 2026-05-31. `3.x` last-modified stamps: `Response.php` 2026-04-09, `ResponseFactory.php`/`PropsResolver.php` 2026-04-30, `Middleware.php` 2026-03-11, `Middleware/EnsureGetOnRedirect.php` 2026-04-09, `Support/Header.php` 2026-02-24, `ScrollProp.php` 2026-03-11, `OnceProp.php` 2025-12-15, `ResolvesOnce.php` 2025-12-10, `config/inertia.php` 2026-04-08. `src/` now has `flash`/`shareOnce`/`transformComponentUsing`/`resolveUrlUsing`/`back`/`rescuedProps` surface. Testing helpers: `AssertableInertia.php`, `ReloadRequest.php`, `TestResponseMacros.php`.
- Prior: `3.x` files read 2026-05-30. Laravel framework `ExcludesPaths` trait read from `laravel/framework@12.x`.

## Comparisons
- [SSR route exclusion](ssr_route_exclusion.md) — Laravel withoutSsr/middleware-except/HttpGateway vs Django http.py; Django MISSING per-path exclusion.
- [sharedProps page-object field](shared_props_metadata.md) — Laravel emits `sharedProps` (Inertia::share key list), default ON; Django mirrors on feat/v3-protocol-completion (http.py build_shared_prop_keys ~L449).
- [Test coverage map](test_coverage_map.md) — Laravel 3.x test files → Django tests; gaps + not-applicable patterns from the 2026-05-30 analysis.
- [Asset version handling](asset_version_handling.md) — Laravel getVersion() (string) cast at ResponseFactory:150-154 + stale check Middleware:148; Django raw value = DIVERGENT bug on numeric INERTIA_VERSION.
- [Validation errors / error bags](validation_errors.md) — Laravel Middleware:68-73,223-247 vs Django _resolve_session_errors/flash_errors: MIRRORED incl. withErrors REPLACE (7475a91) + redirect_back vs Inertia::back; residual gap = named bags only.
- [flash + rescuedProps page fields](flash_and_rescued_props.md) — Laravel `flash` + `rescuedProps` mechanics; Django MIRRORS both incl. rescued-props-drop-merge-metadata (resolveProps continue precedes collectMetadata).
- [Version-change reflash](version_change_reflash.md) — onVersionChange (Middleware:207-216) reflashes pre-409 but can't restore PULLED flash/clearHistory/preserveFragment; Django stash-restore is MORE preserving (benign divergence).
- [Precognition ownership](precognition_ownership.md) — 100% laravel/framework (13.x cites); inertia-laravel 3.x has ZERO precognition code (grep-verified at d51bac8).
