# E2E testing

Manual end-to-end regression checklist for the sample project. Run this whenever the library changes to confirm the v3 protocol surfaces still work. The pages and routes referenced here exist solely to exercise one feature each — do not edit them to fit unrelated changes.

The official protocol reference is <https://inertiajs.com/docs/v3/core-concepts/the-protocol.md>.

## Setup

Two terminals from `sample_project/`:

```bash
# Terminal 1 — Django
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

```bash
# Terminal 2 — Vite
npm run dev
```

Both must be up before driving the browser.

## Driving the browser

Use `playwright-mcp` (e.g. via Claude Code) or any browser. Walk the sections below in order. Keep DevTools' **Network** tab open — many assertions are about request/response headers and JSON shape, not visible UI.

For most steps you'll inspect the JSON returned in an Inertia XHR response. The shape is:

```json
{ "component": "...", "url": "...", "version": "...", "props": { ... },
  "deferredProps": {...}, "mergeProps": [...], "prependProps": [...],
  "deepMergeProps": [...], "matchPropsOn": [...], "onceProps": {...},
  "scrollProps": {...}, "encryptHistory": true, "clearHistory": true,
  "preserveFragment": true }
```

The conditional fields (`deferredProps`, `mergeProps`, …, `encryptHistory`, `clearHistory`, `preserveFragment`) are only emitted when populated / `true`.

---

## 1. Page-shell & always-on shape

| Step | URL / action | Expected |
|------|--------------|----------|
| 1.1 | `/` | Renders `Home`. Greeting shows shared user `Brandon (goalie)` from `share()` middleware, plus library version. |
| 1.2 | View page source on `/` | First-load shell is `<script data-page="app" type="application/json">…</script>` followed by `<div id="app"></div>`. **No** legacy `<div id="app" data-page="…">` form. |
| 1.3 | Inspect the page-shell JSON | `props.errors` is `{}` (always-included key, auto-injected). Conditional fields (`encryptHistory`, `clearHistory`, `preserveFragment`, `deferredProps`, `onceProps`, …) are **absent** unless the view opts in. |
| 1.4 | (Optional XSS canary) Temporarily add `share(request, motto="<script>alert(1)</script>")` and reload `/` | The page-shell text contains `<script>`, never a raw `<script>`. Remove the canary after the check. |

---

## 2. Optional / defer / once / partial-data / partial-except / reset

| Step | URL / action | Expected |
|------|--------------|----------|
| 2.1 | `/lazy/` initial visit (inspect raw HTML, `view-source:`) | Page-shell JSON has props `name`, `plans` (once), `topic` (once + fresh) — `sport` and `team`/`grit` are **absent** from `props` because they're `IgnoreOnFirstLoadProp`. `deferredProps: {"default": ["team"], "extras": ["grit"]}`. `onceProps` has two entries: `plans` (auto key) and `lazy-topic-v1` (custom `key=`, `prop: "topic"`, `expiresAt: null` because `fresh=True` and no `expires_in`). |
| 2.1b | Same page, observe network | The v3 client immediately fires **one partial-data fetch per deferred group** in parallel (e.g. `X-Inertia-Partial-Data: team` and `X-Inertia-Partial-Data: grit`). Each carries `X-Inertia-Except-Once-Props: plans,lazy-topic-v1` automatically — the client always sends this header listing once-keys it has cached. After both fetches resolve, the UI shows `team` and `grit`. |
| 2.2 | Click "Load `sport` (optional)" | Request: `X-Inertia-Partial-Data: sport`, `X-Inertia-Partial-Component: Lazy`. Response `props` contains `sport` and `errors` only. UI now renders `sport: "Basketball"`. |
| 2.3 | Click "Load `team` + `grit` (deferred)" | Request: `X-Inertia-Partial-Data: team,grit` (a single fetch this time — manual `router.reload` does not split per group, only the client's auto-fetch does). Response includes both deferred props. |
| 2.4 | Click "Reload `extras` group only" | Request: `X-Inertia-Partial-Data: grit`. Response includes `grit`; `team` (default group) is untouched in the UI. Confirms group routing. |
| 2.5 | Click "Reset `plans` (once)" | Request: `X-Inertia-Partial-Data: plans` + `X-Inertia-Reset: plans`. Response page-shell carries `onceProps.plans` again with a fresh `expiresAt` regardless of the client-side cache header. |
| 2.6 | Click "Reload except `name`" | Request: `X-Inertia-Partial-Except: name` (the v3 client does **not** also send `X-Inertia-Partial-Data`). Response `props` contains every prop **except** `name`; `errors` is still present (always-included); `deferredProps` is **absent** (server recognizes the request as a partial render off the component header alone, matching Laravel's `PropsResolver`). |
| 2.7 | Navigate `/lazy/` → `/` → `/lazy/` via `Link` | Request includes `X-Inertia-Except-Once-Props: plans,lazy-topic-v1`. Response: `props.plans` is **omitted** (server-side once-skip). `props.topic` is **still present** because `fresh=True` bypasses the skip. |

---

## 3. Merge family + match_on

| Step | URL / action | Expected |
|------|--------------|----------|
| 3.1 | `/lists/` initial visit (inspect raw HTML) | `users`, `notifications`, `filters` are in `props`. `recent_orders` is **missing from `props`** (deferred). Page-shell has `mergeProps: ["users", "recent_orders"]`, `prependProps: ["notifications"]`, `deepMergeProps: ["filters"]`, and `matchPropsOn` containing `users.id`, `notifications.id`, `filters.buckets.id`, `recent_orders.id`. **Note:** the merge metadata for a deferred-merge prop is registered in the **first-load shell**, *before* the deferred fetch resolves — that's the v3 protocol contract: register up front, populate later. `deferredProps.default` lists `recent_orders`. |
| 3.1b | Same page, observe network | The v3 client immediately fires `X-Inertia-Partial-Data: recent_orders` to resolve the deferred prop. Response: `props.recent_orders` populates; the UI now shows the orders. |
| 3.2 | Click "Load `recent_orders` (deferred + merge)" | Manually re-trigger the same partial fetch. Response includes `recent_orders` and keeps it in `mergeProps`. |
| 3.3 | Click "Refresh users" | Partial reload of `users` only. Response keeps `users` in `mergeProps` and `users.id` in `matchPropsOn`. |
| 3.4 | Click "Reset users" | Request: `X-Inertia-Partial-Data: users` + `X-Inertia-Reset: users`. Response page-shell **omits the entire `mergeProps`/`prependProps`/`deepMergeProps`/`matchPropsOn` arrays** for that partial scope (`users` is no longer in `mergeProps`, `users.id` is no longer in `matchPropsOn`). That's how the server tells the client to drop the merged collection on the client side. |

---

## 4. Infinite scroll

| Step | URL / action | Expected |
|------|--------------|----------|
| 4.1 | `/feed/` initial | Five items (`Item 10`–`Item 14`). Page-shell has `scrollProps.items` = `{pageName: "page", previousPage: null, nextPage: 2, currentPage: 1, reset: false}`. `mergeProps` contains `items`. `matchPropsOn` includes `items.id`. |
| 4.2 | Click "Load next page (append)" | Request: `?page=2`, no merge-intent header. Response: items **append** to the list. `scrollProps.items` updates to `previousPage: 1, currentPage: 2, nextPage: 3`. `items` stays in `mergeProps`. |
| 4.3 | Click "Load older (prepend)" | Request header `X-Inertia-Infinite-Scroll-Merge-Intent: prepend`. Response page-shell lists `items` in **`prependProps`**, **not** `mergeProps`. The list prepends. |
| 4.4 | Click "Reset feed" | Request: `X-Inertia-Partial-Data: items` + `X-Inertia-Reset: items`. Response `scrollProps.items.reset === true`. `mergeProps`, `prependProps`, and `matchPropsOn` are **all absent** from the response (no merge metadata for `items` in this partial scope) — server signals client-side reset. |

---

## 5. useForm validation (Inertia-native flow)

| Step | URL / action | Expected |
|------|--------------|----------|
| 5.1 | `/form/` submit empty | UI stays on the form. Errors render inline (`Name is required`, `Email is invalid`). Network: response is a normal **Inertia 200** with component `Form`; JSON has `props.errors = {name, email}` (set by `share(request, errors=...)`). **Address-bar URL becomes `/form/submit/`** because Inertia takes the URL of the 200 response — that is expected, not a bug. Submitting again from the same form re-POSTs to `/form/submit/`. |
| 5.2 | `/form/` submit valid `{name: "x", email: "x@y"}` | Server returns 302 → `/?submitted=1`; v3 client follows. Lands on `Home`. |

---

## 6. errors_response / useHttp validation flow

| Step | URL / action | Expected |
|------|--------------|----------|
| 6.1 | `/validate/` submit empty `name` | Plain XHR `POST /api/validate/` with `Content-Type: application/json` and `X-CSRFToken`. Response is **422 JSON**: `{"message": "The given data was invalid.", "errors": {"name": "Name is required"}}`. **No** Inertia visit happens; the page does not change. UI renders the error inline. The browser will log `Failed to load resource: the server responded with a status of 422` in the console — that is Chrome's default console line for a non-2xx XHR, not an application error. |
| 6.2 | `/validate/` submit `name: "ok"` | Response `200 {"ok": true}`. UI shows "OK (200)". |
| 6.3 | Compare with section 5 | Section 5's response is a 200 Inertia page. Section 6's is a 422 JSON. The library exposes both flows by design — `useForm` for full Inertia visits, `errors_response` for `useHttp`-style XHR. |

---

## 7. Redirects

| Step | URL / action | Expected |
|------|--------------|----------|
| 7.1 | Click `inertia_redirect()` link → `/inertia-redirect/` | Server returns **409** with `X-Inertia-Redirect: /lists/`. v3 client navigates to `/lists/` without a hard reload. |
| 7.2 | Click `location()` link → `/location/` | Server returns **409** with `X-Inertia-Location: https://example.com/`. Browser performs a **hard** navigation off-site. Use the browser back button to return. |
| 7.3 | Click `Fragment redirect (middleware)` link → `/redirect-fragment/` | Server view returns plain `redirect("/lists/#users")` (a 302). **InertiaMiddleware** intercepts on the Inertia request and rewrites to `409 + X-Inertia-Redirect: /lists/#users`. Final URL: `/lists/#users`. |
| 7.4 | Click `preserve_fragment` link `<Link href="/preserve-fragment/#users">` | The view calls `preserve_fragment(request)` then `redirect("/lists/")` (no fragment in `Location`). The follow-up `/lists/` Inertia response includes **`preserveFragment: true`**. v3 client carries the original `#users` fragment to `/lists/`. Final URL: `/lists/#users`. |

---

## 8. History controls

| Step | URL / action | Expected |
|------|--------------|----------|
| 8.1 | `/history/` | Page-shell JSON contains `encryptHistory: true` (the view called `encrypt_history(request)`). `clearHistory` is absent. |
| 8.2 | Click "Clear history (server-flash → redirect)" → `/clear-history/` | Server stamps a session flag and 302s to `/history-after-clear/`. The follow-up `History` response contains `clearHistory: true` (consumed once from session). |
| 8.3 | Reload `/history-after-clear/` directly | `clearHistory` is **absent** — the session flash is one-shot. |

---

## 9. Method conversion (303 on PUT/PATCH/DELETE redirects)

| Step | URL / action | Expected |
|------|--------------|----------|
| 9.1 | `/method/` click "PUT /method/submit/" | XHR is `PUT`. Server view returns 302 to `/?method=put`; **InertiaMiddleware** converts the response status to **303** (per the v3 protocol). v3 client follows the 303 with a `GET` and lands on `Home`. |
| 9.2 | Same with PATCH | Final URL: `/?method=patch`. Status on the redirect response is **303**. |
| 9.3 | Same with DELETE | Final URL: `/?method=delete`. Status on the redirect response is **303**. |

---

## 10. Stale version refresh

The library compares the request's `X-Inertia-Version` against the configured `INERTIA_VERSION`. A mismatch on a `GET` Inertia request triggers a hard reload (so the SPA gets a fresh asset bundle).

| Step | URL / action | Expected |
|------|--------------|----------|
| 10.1 | Stop Django. Restart with `INERTIA_VERSION=2.0 python manage.py runserver 0.0.0.0:8000`. | Server now advertises `version: "2.0"` in fresh page-shells. |
| 10.2 | Open a new tab on `/` to seed a v2 client. Then in the seeded tab navigate via `Link` to any other route. | Request carries `X-Inertia-Version: 2.0` matching server — normal navigation. |
| 10.3 | Without restarting Django, edit `sample/settings.py` and bump to `INERTIA_VERSION = os.getenv("INERTIA_VERSION", "3.0")`, restart server with `INERTIA_VERSION=3.0`. | Now the seeded tab's client still thinks version is `2.0`. |
| 10.4 | In the seeded tab, click any `Link` | Server responds **409 + `X-Inertia-Location: <full URL>`**. v3 client performs a hard reload, which fetches a fresh page-shell with `version: "3.0"`. |
| 10.5 | Restart Django with `INERTIA_VERSION=1.0` (the default) for the rest of the checklist. | Standard navigation resumes. |

---

## Cross-cutting assertions to watch for

These are not separate steps — verify them while running the checklist above.

- **Page-shell.** `<script data-page="app" type="application/json">…</script>` followed by `<div id="app"></div>`. The v3 client refuses to boot from the legacy `<div id="app" data-page="…">` form.
- **JSON escape.** Any `<`, `>`, `&` inside the page-shell JSON is escaped to `<`, `>`, `&`. Section 1.4 has the canary check.
- **Always-included `errors`.** Every Inertia response carries `props.errors`. It survives `X-Inertia-Partial-Data` filtering. It is removed only when explicitly listed in `X-Inertia-Partial-Except`.
- **Only-when-true emission.** `encryptHistory`, `clearHistory`, `preserveFragment` are absent unless `true` (v3 spec).
- **CSRF.** Every XHR — Inertia visits via `useForm`/`router.*` and `useHttp`-style XHRs in section 6 — carries `X-CSRFToken` sourced from the `csrftoken` cookie. Django returns 403 if missing.
- **No console errors.** v3 client throws fast on a malformed page-shell. Any "Cannot read properties of null (reading 'component')" on first load means the JSON `<script>` tag isn't reaching the browser.
- **Response status codes.** 200 for normal Inertia visits; 409 for `inertia_redirect` / `location` / fragment-redirect / stale-version; 303 for non-POST redirects (section 9); 422 for `errors_response` (section 6).

---

## Notes on running the canary checks

- **XSS escape canary (section 1.4) is best-effort.** The library escapes `<`, `>`, `&`, and `/` in the page-shell JSON (`inertia/http.py:362-371`), but a clean response body has no chars to escape, so a plain run won't prove it. The `/` escape *is* observable on every run because every page-shell contains URL/path strings (e.g. `"url": "/"`). For `<`, `>`, `&`: temporarily edit `sample/apps/core/middleware.py` `ShareDemoMiddleware` to inject e.g. `motto="<script>alert(1)</script>"`, reload `/`, and grep the page source for `\\u003c` (escaped) — never raw `<script>alert`.

---

## Coverage map (which feature each section exercises)

| Section | Library symbol(s) / protocol surface |
|---------|--------------------------------------|
| 1 | page-shell `<script>`, `INERTIA_LAYOUT`, `share()`, auto-injected `errors`, conditional-field emission, JSON escape |
| 2 | `optional()`, `defer()` (default + custom group), `once()` (auto key, custom `key=`, `fresh=True`, `expires_in=`), `X-Inertia-Partial-Data`, `X-Inertia-Partial-Except`, `X-Inertia-Reset`, `X-Inertia-Except-Once-Props` |
| 3 | `merge()`, `prepend()`, `deep_merge()`, `match_on=` (flat & dotted), `defer(..., merge=True, match_on=...)`, `X-Inertia-Reset` against `mergeProps`, `matchPropsOn` |
| 4 | `infinite_scroll()`, `scrollProps`, `X-Inertia-Infinite-Scroll-Merge-Intent`, `match_on=`, `X-Inertia-Reset` against `scrollProps` |
| 5 | `@inertia` decorator with redirect return, `share(errors=...)`, `useForm` flow |
| 6 | `errors_response()`, plain XHR / `useHttp` flow, 422 JSON shape |
| 7 | `inertia_redirect()`, `location()`, `InertiaMiddleware` fragment-redirect rewrite, `preserve_fragment()` |
| 8 | `encrypt_history()`, `clear_history()`, session-flash one-shot consumption |
| 9 | `InertiaMiddleware` 302→303 conversion on PUT/PATCH/DELETE |
| 10 | `INERTIA_VERSION` mismatch → 409 `X-Inertia-Location` |
