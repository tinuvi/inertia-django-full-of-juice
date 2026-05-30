---
name: reference-sha
description: Laravel inertia-laravel 3.x reference points last compared against, with dates
metadata:
  type: reference
---

Canonical Laravel adapter compared against: `inertiajs/inertia-laravel`, branch `3.x`.

Key SSR-exclusion source (as of review on 2026-05-30):
- `src/Ssr/HttpGateway.php` — `dispatch()` returns `null` when `ssrIsEnabled()` is false; `ssrIsEnabled()` = `$enabled && ! $this->inExceptArray($request)`. File last modified 2026-04-08 (Pascal Baljet). The gateway uses the `ExcludesPaths` trait; `withoutSsr` populates `$except` via `except()`.
- `Illuminate\Foundation\Http\Middleware\Concerns\ExcludesPaths::inExceptArray` (laravel/framework) — `trim($except,'/')` then `$request->fullUrlIs($except) || $request->is($except)`. `Str::is` glob, whole-string anchored, leading/trailing slash stripped from the pattern.

When SSR is excluded, Laravel's caller falls back to the same non-SSR HTML shell. Observable wire result of exclusion == client-side-only shell, no POST to SSR server.

See [[divergence-ssr-exclude-regex-vs-glob]] for the accepted Django divergence.
