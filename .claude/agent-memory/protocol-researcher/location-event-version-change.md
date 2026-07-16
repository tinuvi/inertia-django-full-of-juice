---
name: location-event-version-change
description: v3.6.0+ 409 location responses — the undocumented X-Inertia-Version echo, versionChange, async suppression scope (prefetch is the exception), and safe-echo edge cases
metadata:
  type: reference
---

# `location` event + `versionChange` (client v3.6.0+, PR #3180)

Shipped in **@inertiajs/core 3.6.0** (npm 2026-07-02T14:56Z; commit `36a5438` merged 2026-07-02T13:18Z). Re-verified against 3.x HEAD on 2026-07-16: `response.ts`'s newest commit is still `36a5438` — no drift through 3.6.1 (3.6.1's 2026-07-07 commit touched only xhr/axios clients). Repo default branch = `3.x` (gh api).

## The undocumented server obligation (IMPORTANT for this adapter)

On a **409 asset-version-mismatch** response, the server should **echo the CURRENT server asset version in `X-Inertia-Version`** (not the client's stale one — echoing the request header back keeps `versionChange` false and deads the feature).

- **Still undocumented as of 2026-07-16.** Protocol page 409 example (`/v3/core-concepts/the-protocol.mdx` L481-489) shows RESPONSE = `409: Conflict` + `X-Inertia-Location` only; header table lists X-Inertia-Version request-side only (L102). `asset-versioning.mdx` L31-33 documents the behavior ("v3.6.0+ A version change detected on a background request … does not force a full-page navigation"), not the mechanism. `events.mdx` L662-722 documents the event, silent on derivation.
- Laravel ref (verified at 3.x HEAD): `src/Middleware.php` `onVersionChange()` L207-219 — `Inertia::location($request->fullUrl())` then `headers->set(Header::VERSION, Inertia::getVersion())`. Echo lives there ONLY; plain `Inertia::location()` and `onRedirectWithFragment()`'s 409 (L197-202) carry no version header. Version check L149: `$request->header(Header::VERSION, '') !== Inertia::getVersion()`.

**No header ⇒ `versionChange` always false ⇒** (1) async/background requests fall through to `window.location.reload()` (suppression dead, fails open); (2) `inertia:location` `detail.versionChange` lies (false on genuine deploys) even for SYNC visits — breaks the documented cancel-event/"banner" pattern (`events.mdx` L689+).

## Client wire behavior — `packages/core/src/response.ts` (3.x)

`locationVisit` L204-231: SSR guard → `responseVersion = this.getHeader('x-inertia-version')` (L210) → `versionChange = !!responseVersion && responseVersion !== currentPage.get().version` (L211) → cancelable `fireLocationEvent(url, versionChange)` → `if (versionChange && this.requestParams.all().async) return` (~L219) → SessionStorage locationVisitKey → `reload()` / `href = url.href`. Whole body try/catch.

- Reached only via `process()` `!isInertiaResponse()` → `handleNonInertiaResponse()` (L68-70, L140): so the 409 must NOT carry `X-Inertia: true`, and `x-inertia-redirect` on a 409 takes precedence over `x-inertia-location` (L141 before L151).
- `getHeader` is exact-key lookup (L185-187); lowercase keys are the HttpClient's contract. Default `XhrHttpClient` (`http.ts` L6) lowercases in `parseHeaders` (`xhrHttpClient.ts` L29); optional axios client lowercases in `normalizeHeaders` (`axiosHttpClient.ts` L23). Custom user clients could violate this.
- 4xx/5xx REJECT at the client (`xhrHttpClient.ts` L170-176); `request.ts` L88-95 catches `HttpResponseError` → `Response.create(...).handle()` — so 409s still flow into `locationVisit`.
- Empty echo is safe: xhr parses `X-Inertia-Version: ` to `''`; `!!''` false → navigates same as no header.

## Suppression scope — which requests are `async: true`

`router.ts`: ordinary visits default `async: false` (L702). `doReload` sets `async: true` (L165) → backs `router.reload()` (L147), poll ticks (`poll()` L226-248, `poll: true` L233; `poll.ts` is a pure timer), `loadDeferredProps` (L820-825), `<WhenVisible>` (adapters call `router.reload`, e.g. react `WhenVisible.ts` L74), infinite scroll. `prefetch()` L385 / `getPrefetchParams()` L664 also `async: true`, BUT:

**Prefetch is the exception — a 409 during prefetch never reaches `locationVisit` at fetch time.** `process()` short-circuits prefetch responses before the `isInertiaResponse` check (response.ts L55-63: sets `wasPrefetched`, clears `prefetch`, `onPrefetched`, returns). `prefetched.ts` `add()` caches the 409 Response unconditionally (no status validation); `handlePrefetch()` re-handles only if prefetched URL == window.location (race). At use-time `use()` L191-215 → `mergeParams(consumedParams)` where `RequestParams.merge` is a spread overwrite (`requestParams.ts` L172-177) → consuming click's `async: false` replaces `async: true` → navigates at click time, header or not (user-initiated, correct).

## Sole read; safe to echo only on the version-mismatch 409

Enumerated every header read in `response.ts`: `x-inertia-redirect` (L142), `x-inertia-location` (L152), `x-inertia` (hasHeader ~L173), `x-inertia-version` (L210 — ONLY inside `locationVisit`). GitHub code search over 3.x `packages/core`: header appears only in `request.ts` (request-side write, `page.version && headers['X-Inertia-Version'] = page.version`) and this read. No prefetch validation / history / non-409 path reads it → force_refresh-only echo cannot interact elsewhere. Echoing inside generic location() would mislabel manual redirects as version changes when the client is deploy-stale → async requests would silently swallow manual redirects (docs: header distinguishes "automatic asset version change … from a manual redirect").

## Public event

`GlobalEventsMap.location` (`types.ts` L457-463): `details: { url: URL; versionChange: boolean }`, fired as `inertia:location`, cancelable (`events.ts` L66). Docs `/v3/advanced/events.mdx` L662+.
