---
name: ssr-route-exclusion
description: How Laravel inertia-laravel 3.x excludes routes from SSR (withoutSsr / middleware except / HttpGateway) vs Django http.py
metadata:
  type: project
---

Laravel "Excluding Routes from SSR" lives entirely in the SSR gateway, not the page object or HTML shell. Path matching is delegated to Laravel's framework trait, so wildcards are URL-glob semantics, not regex.

**Why:** User is building the Django equivalent in inertia-django-full-of-juice. They want to mirror Laravel's mechanism for excluding routes from SSR.

**How to apply:** When designing/reviewing the Django feature, mirror these Laravel facts (all branch `3.x`, last-checked SHA noted in MEMORY.md):

- Developer API (two entry points, both feed the same `except` accumulator):
  - `Inertia::withoutSsr(array|string $paths)` — `src/ResponseFactory.php:224-233`. Throws `LogicException` if gateway is not an `ExcludesSsrPaths`. Calls `$gateway->except($paths)`.
  - Middleware property `protected $withoutSsr = []` — `src/Middleware.php:39`. Applied in `handle()` at `src/Middleware.php:134-136`: `if (! empty($this->withoutSsr) && $ssrGateway instanceof ExcludesSsrPaths) { $ssrGateway->except($this->withoutSsr); }`.
- Contract: `interface ExcludesSsrPaths { public function except(array|string $paths): void; }` — `src/Ssr/ExcludesSsrPaths.php`. Sibling interface `DisablesSsr { disable(Closure|bool) }` (`src/Ssr/DisablesSsr.php`) is the conditional on/off switch — distinct from path exclusion.
- Implementation: `HttpGateway implements DisablesSsr, ExcludesSsrPaths, Gateway, HasHealthCheck` (`src/Ssr/HttpGateway.php:16`); `use ExcludesPaths` (Laravel framework trait). `protected $except = []` (L26). `except()` merges via `Arr::wrap` (L98-101).
- Exclusion check point: `HttpGateway::dispatch()` returns `null` early (`src/Ssr/HttpGateway.php:40`) when `ssrIsEnabled()` is false. `ssrIsEnabled()` (L143-150): `return $enabled && ! $this->inExceptArray($request);`. Returning null from dispatch = SSR skipped, falls back to client-side shell.
- Matching semantics: `Illuminate\Foundation\Http\Middleware\Concerns\ExcludesPaths::inExceptArray($request)` — for each pattern (trimmed of `/` unless it is `/`), matches if `$request->fullUrlIs($except) || $request->is($except)`. So patterns match against BOTH the full URL and the path, using Laravel `Str::is` glob (`*` wildcards), e.g. `admin/*`, `nova/*`. Not route names, not regex. `getExcludedPaths()` returns `$this->except`.
- Effect on output: route excluded => no SSR HTTP call => no server-rendered `body`/`head`. Root element still gets the `data-page` JSON; page hydrates/renders client-side only. The exclusion is a runtime gateway decision, NOT a Blade directive change.
- Config surface: `config/inertia.php` `'ssr'` block has `enabled`, `runtime`, `ensure_runtime_exists`, `url`, `ensure_bundle_exists`, `bundle`, `throw_on_error`. There is NO config key for excluded paths — exclusion is code-only (`withoutSsr` / middleware `$withoutSsr`). `ssr.enabled` (env `INERTIA_SSR_ENABLED`, default true) is the global toggle.
- Version note: gateway-based exclusion (`ExcludesSsrPaths`/`withoutSsr`) is a 3.x-era feature, sibling to `DisablesSsr`/`disableSsr`. Not present in 0.x/1.x adapters.

Django counterpart (divergent/missing): `inertia/http.py:443 build_first_load_context_and_template` is the SSR call site. It only checks the global `settings.INERTIA_SSR_ENABLED` (`inertia/settings.py:14`, default False) before POSTing to `INERTIA_SSR_URL/render`. There is NO per-path exclusion, no `withoutSsr` helper, no middleware path list. See [[ssr-config-surface]].
