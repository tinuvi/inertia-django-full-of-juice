---
name: once-props
description: v3 once-props wire behavior — when client sends X-Inertia-Except-Once-Props, cached-value merge, reset interplay, expiresAt unit, fresh semantics
metadata:
  type: reference
---

# Once props (spec: /v3/data-props/once-props.mdx + the-protocol.mdx; client: inertiajs/inertia 3.x packages/core)

## Header emission (X-Inertia-Except-Once-Props)
- Built in `Request.getHeaders()` (`packages/core/src/request.ts` ~L160-190) → sent on EVERY Inertia XHR (visits, plain reload, partials, non-GET, prefetch). Not gated on partial.
- Value = registry KEYS (effective keys, not prop names) of current page's `onceProps`, filtered: prop value present in `page.props` (skips not-yet-loaded deferred once) AND `!expiresAt || expiresAt > Date.now()`. Joined with `,`. Header omitted entirely when list empty.
- Spec: header = "Comma-separated list of non-expired once prop keys already loaded on the client. The server will skip resolving these props unless explicitly requested via a partial reload or force refreshed server-side." (the-protocol.mdx, Request Headers).

## Cached-value reuse when server omits the prop
- Server must STILL emit the `onceProps` registry entry while omitting the prop from `props` (protocol example: "plans is included in onceProps but not in props").
- Client `CurrentPage.mergeOncePropsIntoResponse(response, {force})` (`packages/core/src/page.ts` ~L341-354): for each response registry entry with a matching cached entry, if `force` or response props lack the value → `set(response.props, onceProp.prop, get(this.page.props, existingOnceProp.prop))` and restores cached `expiresAt` onto the response entry. Called from `response.ts setPage()` (~L230) on every successful response, and from prefetch (`prefetched.ts` ~L75; force:true in `updateCachedOncePropsFromCurrentPage` ~L283).
- Cross-page custom keys work because merge reads via the EXISTING entry's `prop` name, writes via the response entry's `prop` name.
- No registry entry in a full (non-partial) response → value forgotten ("Navigating to a page without the once prop will forget the remembered value" — once-props.mdx).
- On partials (same component) `mergeProps()` also carries registry over: `pageResponse.onceProps = {...current.onceProps, ...response.onceProps}` (`response.ts` ~L421-427; guard `isPartial() && same component` ~L328-330).

## reset interplay (gotcha)
- `requestParams.ts`: `isPartial()` = only/except/RESET non-empty (~L62-64); `const only = this.params.only.concat(this.params.reset)` → reset keys land in `X-Inertia-Partial-Data` too (~L135-139); `X-Inertia-Reset` = reset.join(',') (~L145-147).
- So `reload({reset:['plans']})` sends Partial-Component + `X-Inertia-Partial-Data: plans` + `X-Inertia-Reset: plans` + UNCHANGED `X-Inertia-Except-Once-Props` (getHeaders never consults reset; client does NOT drop its once cache pre-request).
- Server recompute path is the partial-data inclusion ("The server will always resolve a once prop when explicitly requested" — once-props.mdx recommends `reload({only:[...]})` for refresh; reset works because it rides Partial-Data). reset names = PROP names, except-once = effective keys.

## expiresAt / fresh
- `expiresAt?: number | null` (`types.ts` ~L248-254) — epoch MILLISECONDS (compared to `Date.now()`). After expiry client silently stops listing the key → server re-resolves. Prefetch cache eviction uses shortest once TTL (`prefetched.ts getShortestOncePropTtl`).
- `fresh` does not exist client-side. Purely server: server re-sends the value despite except-once; client merge sees value present → keeps server value (and the response entry's own expiresAt).

## Django adapter shape (inertia/http.py build_once_props ~L293-323)
- `onceProps[effective_key] = {"prop": prop_name, "expiresAt": int_ms | None}` — expiresAt key ALWAYS present, None when unset (test: tests/test_tests.py L68). `once()` converts expires_in/expires_at to epoch ms (`inertia/utils.py` L93-123). Drops registry entry when prop name in X-Inertia-Reset; build_props resends value when in Partial-Data or fresh=True — matches client expectations above.
