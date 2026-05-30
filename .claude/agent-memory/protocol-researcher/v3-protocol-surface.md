---
name: v3-protocol-surface
description: Complete enumeration of the Inertia v3 protocol surface (request/response headers, page-object fields, status codes) with spec citations
metadata:
  type: reference
---

# Inertia v3 protocol surface (spec: https://inertiajs.com/docs/v3/core-concepts/the-protocol.md)

## Request headers (server must honor)
- `X-Inertia` (bool) — marks Inertia XHR.
- `X-Requested-With` = XMLHttpRequest.
- `Accept` = text/html, application/xhtml+xml.
- `X-Inertia-Version` — asset version, drives 409 stale check.
- `Purpose` = `prefetch` on prefetch requests.
- `X-Inertia-Partial-Component` — component name for partial reloads.
- `X-Inertia-Partial-Data` — CSV props to include.
- `X-Inertia-Partial-Except` — CSV props to exclude (takes precedence over Partial-Data).
- `X-Inertia-Reset` — CSV props to reset on navigation.
- `Cache-Control` = no-cache for reload requests.
- `X-Inertia-Error-Bag` — which error bag to namespace validation errors under. Client sends only when errorBag set (`packages/core/src/requestParams.ts`).
- `X-Inertia-Infinite-Scroll-Merge-Intent` — append|prepend.
- `X-Inertia-Except-Once-Props` — CSV non-expired once keys already on client.
- Precognition / Precognition-Validate-Only — Precognition validation requests.

## Response headers (server should send)
- `X-Inertia` = true.
- `X-Inertia-Location` — 409 external redirect → full window.location visit.
- `X-Inertia-Redirect` — 409 fragment redirect → standard Inertia visit (preserves #fragment).
- `Vary` = X-Inertia.
- Precognition / Precognition-Success — Precognition responses (204 on success).

## Asset versioning (X-Inertia-Version + 409)
- Page `version` type: spec doc table says `string|number`; client `Page.version: string | null` (`packages/core/src/types.ts` ~L235). On the wire (JSON/data-page) the server serializes it; client treats it as the opaque version token.
- Client sends header only when truthy: `if (page.version) { headers['X-Inertia-Version'] = page.version }` (`packages/core/src/request.ts` ~L168). Null/empty/absent version => header NOT sent. First full-page load is a plain browser request with no Inertia headers (spec L3); header starts appearing once a version was given from back-end (tests/links.spec.ts).
- Server compares header to its current version; equal => continue; different => "immediately returns a 409 Conflict response, and includes the URL in a X-Inertia-Location header." Spec: "409 Conflict responses are only sent for GET requests, and not for POST/PUT/PATCH/DELETE requests... they will be sent in the event that a GET redirect occurs after one of these requests." (v3/advanced/asset-versioning.mdx L381-383; mirrored in the-protocol.mdx).
- Client 409 reaction: `isLocationVisit() = hasStatus(409) && hasHeader('x-inertia-location')` then `locationVisit(url)`: if same URL sans hash `window.location.reload()` else `window.location.href = url.href` (`packages/core/src/response.ts` ~L194-214). No client-side method check — the GET-only gate is purely a server obligation.
- Spec is SILENT on how server treats a MISSING/empty X-Inertia-Version. Laravel ref treats missing header as `''` and only 409s when `$request->header('X-Inertia-Version','') !== version`; so a versionless request vs a versioned server WOULD mismatch in Laravel. Django lib treating missing-as-match is a divergence from Laravel (spec itself does not dictate this).
- Reflash: "If 'flash' session data exists when a 409 Conflict response occurs, Inertia's server-side framework adapters will automatically reflash this data." (asset-versioning.mdx L383).

## Page object fields
component, props (always incl errors:{}), url, version — always.
Only-when-set: encryptHistory(true), clearHistory(true), preserveFragment(true),
mergeProps[], prependProps[], deepMergeProps[], matchPropsOn[], scrollProps{},
deferredProps{}, rescuedProps[], sharedProps[], onceProps{}.
- onceProps entry: `{key: {prop: name, expiresAt: ms|null}}`.
- scrollProps entry: `{pageName, previousPage, nextPage, currentPage}` (spec example has NO `reset` key — Django lib adds `reset`).
- rescuedProps[] — deferred props with rescue:true that threw; omitted from props, key listed here. Client renders <Deferred> rescue slot. Client defaults to [] when omitted (`packages/core/src/page.ts`, `response.ts`: `rescuedProps: data.rescuedProps ?? []`).
- sharedProps[] — top-level keys from Inertia::share(); client carries them over on instant visits (`packages/core/src/router.ts`).

## Status codes
- 200 — standard.
- 302 — standard redirect; adapter converts to 303 after PUT/PATCH/DELETE.
- 303 — redirect after non-GET.
- 409 — asset mismatch (X-Inertia-Location), external redirect, or fragment redirect (X-Inertia-Redirect). "409 Conflict responses are only sent for GET requests, and not for POST/PUT/PATCH/DELETE requests. That said, they will be sent in the event that a GET redirect occurs after one of these requests."
- 204 / 422 — Precognition validation.

## Client wire behavior (3.x core)
- `isLocationVisit() = hasStatus(409) && hasHeader('x-inertia-location')` (`packages/core/src/response.ts`) — status+header only, no client-side method gate. GET-only 409 is a server middleware obligation.
- `isInertiaRedirect()` triggers `router.visit(x-inertia-redirect, method:'get')`.
