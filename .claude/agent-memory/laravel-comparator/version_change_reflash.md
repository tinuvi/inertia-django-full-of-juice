---
name: version-change-reflash
description: Laravel onVersionChange (Middleware.php L207-216) blanket-reflashes the session before the 409, but CANNOT restore values the discarded render already pulled (flash/clearHistory/preserveFragment); Django's stash-and-restore force_refresh is strictly more preserving.
metadata:
  type: project
---

Verified 2026-06-10 against `inertiajs/inertia-laravel` branch `3.x` (content identical to SHA `d51bac8`, 2026-06-04 readings; Middleware.php = 249 lines).

## Laravel facts
- `src/Middleware.php` L207-216 `onVersionChange()`: `if ($request->hasSession()) { $session = $request->session(); $session->reflash(); } return Inertia::location($request->fullUrl());`
- Version check runs ONLY AFTER `$next($request)` (L138 → L149-151), gated on `X-Inertia` (L145-147) + `method === 'GET'` + `header(VERSION,'') !== Inertia::getVersion()`. No pre-controller check anywhere in 3.x. Controller always executes; its response is discarded.
- `laravel/framework@12.x` `src/Illuminate/Session/Store.php` L503-508 `reflash()`: `mergeNewFlashes($this->get('_flash.old', [])); $this->put('_flash.old', []);` — re-marks KEY NAMES only. It cannot resurrect a VALUE already removed from attributes by `pull()`.
- Destructive render-time pulls in 3.x (all happen inside `$next`, BEFORE onVersionChange):
  - flash: `Response.php` L239-244 `resolveFlashData()` → `Inertia::pullFlashed()` (`ResponseFactory.php` L489-494, plain `session()->pull`, no stash).
  - clearHistory + preserveFragment: `Response::__construct` does `session()->pull(SessionKey::CLEAR_HISTORY, false)` / `pull(SessionKey::PRESERVE_FRAGMENT, false)`. These are written via plain `session([...])` PUT (`ResponseFactory::clearHistory()`/`preserveFragment()`), NOT `flash()` — so `reflash()` never governs them at all.
  - errors: `resolveValidationErrors` L230 uses non-destructive `session()->get('errors')` → value survives → reflash carries it across the 409. This is the case the reflash actually rescues.
- Net Laravel behavior on stale-version 409 after an Inertia page render: validation errors SURVIVE; un-pulled user flash keys SURVIVE; `inertia.flash_data` VALUE IS LOST (pulled into the discarded body); clearHistory/preserveFragment signals LOST.
- `Inertia::location()` = `ResponseFactory.php` L388-395: X-Inertia request → `409` + `X-Inertia-Location`; else external redirect.

## Django counterpart (inertia/middleware.py, inertia/http.py)
- `middleware.py` L104-112 `force_refresh()`: messages `storage.used = False` + `reflash_one_shot_state()` + `location(request.build_absolute_uri())` (= Laravel's `fullUrl()`).
- L114-161 `reflash_one_shot_state()`: restores `_pulled_flash`/`_pulled_errors`/`_pulled_clear_history`/`_pulled_preserve_fragment` stashed on the response by `http.py` (stash fields L119-122; pops at L160-174, L361/368, L393/400).
- Verdict: MATCHES Laravel on errors + intent; DIVERGES IN DJANGO'S FAVOR on the pulled one-shots — Laravel observably drops flash/clearHistory/preserveFragment across a stale 409, Django restores them. Commit-body citation when formalizing: `Middleware.php:212` (reflash) + `ResponseFactory.php:489-494` (pullFlashed leaves no stash).
- Minor ordering diff: Laravel = version-409 (L149) BEFORE fragment-redirect-409 (L161); Django checks fragment first (`middleware.py` L46 vs L63). Observable only for stale GET whose response is a redirect-with-fragment: Laravel emits `X-Inertia-Location: fullUrl`, Django emits `X-Inertia-Redirect: target`. Both converge after one extra hop.
- Missing-header diff (see [[asset-version-handling]]): Laravel defaults absent `X-Inertia-Version` to `''` → 409 when server version non-empty; Django `is_stale` defaults to server version → no 409.
