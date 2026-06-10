---
name: flash-shared-rescued
description: flash / sharedProps / rescuedProps page-object fields — shape, lifecycle, client consumption, absence tolerance, version they shipped (3.x client citations)
metadata:
  type: reference
---

# flash / sharedProps / rescuedProps (v3 page-object fields)

All inertia cites = inertiajs/inertia branch 3.x; client released at @inertiajs/react 3.3.1.

## flash — object map, NOT in the protocol page-object table (doc gap)
- Shape: `flash: FlashData` (object key→unknown), REQUIRED in client `Page` type (core/types.ts L247) but defaulted: `flash: data.flash ?? {}` on every response (core/response.ts L132 getPageResponse) and on init (core/page.ts L35). Absence fully tolerated.
- DIVERGENCE: the protocol page's Page Object table (the-protocol.mdx L200-280) lists NO `flash` row, yet the wire payload carries it; documented instead at /v3/data-props/flash-data ("Flash data is available on page.flash").
- Lifecycle: replaced wholesale by each response's flash (partial reloads included — "let regular partial reloads use whatever the server sent (which may be empty, clearing stale flash)" core/response.ts L429-434); EXCEPT deferred-props background requests which carry current flash forward (same lines). Stripped from history state (`pageForHistory = { ...page, flash: {} }` core/page.ts L95-96; also history.remember/eventHandler use getWithoutFlashData) ⇒ back/forward restores have empty flash.
- Events/APIs: after setPage, when non-empty and not a deferred-props request → `fireFlashEvent(flash)` + visit `onFlash` callback (core/response.ts L91-96); global `flash` event detail `{flash}` non-cancelable (core/events.ts L58-60, core/types.ts L435-441, events.mdx "Flash"); first-load fires via queueMicrotask (core/initialVisit.ts ~L107-114); `onFlash` in VisitCallbacks (types.ts L490). Client-side `router.flash(keyOrData, value?)` merges into current flash + fires event (core/router.ts L518-540); client-side visits accept `flash` option, default `{}` (performClientVisit L577, fires at L592-597). React: `usePage().flash` (react/usePage.ts L5-13); adapter re-renders via router.init onFlash (react/App.ts L108-117). Shipped in v3.0.0.

## sharedProps — string[] of top-level prop keys, optional
- Spec: "Array of top-level prop keys registered via Inertia::share(). Used by the client to carry shared props over during instant visits." (the-protocol.mdx L262-264). Client type `sharedProps?: string[]` (types.ts L245).
- SOLE consumer: `performInstantSwap` (core/router.ts L613-649): `(current.sharedProps ?? []).filter(k => k in current.props)` → seeds the intermediate page's props (L616-624); intermediate page also propagates `sharedProps: current.sharedProps` (L639) and sets `flash: {}` / `rescuedProps: []` (L635-636). Also passed as 2nd arg to a `pageProps` callback. Nothing else reads it (no usePage API, no flush logic).
- Absence: tolerated via `?? []`; instant visits then start from pageProps/empty props only. Officially toggleable server-side: Laravel `expose_shared_prop_keys => false` (instant-visits.mdx L178-186). Shipped in v3.0.0.

## rescuedProps — string[] of deferred-prop keys that threw and were rescued
- Spec: emitted when `Inertia::defer(fn, rescue: true)` resolver throws → prop omitted from props, key listed in `rescuedProps`; exception reported server-side (the-protocol.mdx L256-258 + L319-331 example; deferred-props.mdx "Error Handling" L194-247).
- Client: `rescuedProps: string[]` required-but-defaulted (`?? []` at page.ts L35, response.ts L132). On partial reloads merged: keep current rescued keys EXCEPT ones this reload re-requested, union incoming (response.ts L441 + mergeRescuedProps L444-455) — a successful retry clears the key. Consumption: `<Deferred>` only — `rescuedKeys = new Set(page.rescuedProps)`; render order: props defined && !rescued → children; rescued && rescue slot → rescue({reloading}); else fallback (react/Deferred.ts L32, L64-79; vue3/svelte same). NO events, NO automatic retry (docs show manual `router.reload({only:[...]})`), no useDeferred hook.
- Absence: tolerated; rescue slot simply never renders. Shipped in v3.1.0 (absent from types.ts at tag v3.0.0; present at v3.1.0 types.ts L235).
- Merge-metadata interplay (verified at v3.3.1): client mergeProps pipeline runs only when `requestParams.isPartial() && same component` (response.ts L328-331); for each listed key `incomingProp = get(pageResponse.props, prop)` — an absent incoming value (e.g. a rescued key) is `undefined` ⇒ neither the Array nor the object branch fires ⇒ NO-OP. So a server listing a rescued key in mergeProps is harmless client-side, but Laravel omits it (rescued `continue` precedes collectMetadata); `<Deferred>`/`mergeRescuedProps` consume only `page.props` + `page.rescuedProps`, never merge metadata.
