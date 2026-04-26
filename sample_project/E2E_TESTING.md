# E2E testing

Manual end-to-end regression checklist for the sample project. Run this whenever the library changes to confirm the v3 protocol surfaces still work. The pages and routes here exercise one feature each — do not edit them to fit unrelated changes.

For ambiguous protocol questions, ask the `protocol-researcher` subagent (citing v3 spec) and the `laravel-comparator` subagent (citing `inertiajs/inertia-laravel` 3.x).

---

## How this checklist asserts behavior

Two channels — both must agree on every step:

1. **Network / DOM** — what the v3 client and browser observe (DevTools Network tab, response headers, page-shell JSON shape).
2. **Library DEBUG logs** — `inertia_django_full_of_juice` emits one DEBUG record per protocol decision (partial filter applied, once skip, deferred suppression, merge metadata reset, fragment-redirect rewrite, 302→303 conversion, stale-version refresh, etc.). The sample project pre-wires this logger to console with the prefix `[inertia] DEBUG …` (see `sample/settings.py:LOGGING`).

Each row below names the **expected log substring** to grep for after the action. If the substring is missing, the library did not take the path the doc claims and the test fails — even if the UI looks right.

---

## Setup

Two terminals from `sample_project/`:

```bash
# Terminal 1 — Django (force unbuffered + disable autoreloader so the
# [inertia] DEBUG logs appear in real time and stay deterministic).
source .venv/bin/activate
python -u manage.py runserver --noreload 0.0.0.0:8000
```

```bash
# Terminal 2 — Vite
npm run dev
```

> **Why `python -u --noreload`** — Django's autoreloader and Python's
> default stderr line-buffering interleave / drop DEBUG records under
> load. With `-u` (unbuffered) and `--noreload` the log channel is
> single-process and synchronous, which is what the assertions below
> require.

Both servers must be up before driving the browser.

## Driving the browser

Use `playwright-mcp`. Walk the sections in order. Keep DevTools' **Network** tab open in parallel for the few rows that assert request headers the v3 client adds.

The page-shell JSON shape:

```json
{ "component": "...", "url": "...", "version": "...", "props": { ... },
  "deferredProps": {...}, "mergeProps": [...], "prependProps": [...],
  "deepMergeProps": [...], "matchPropsOn": [...], "onceProps": {...},
  "scrollProps": {...}, "encryptHistory": true, "clearHistory": true,
  "preserveFragment": true }
```

The conditional fields are only emitted when populated / `true` — the library's `page-shell:` log line lists them under `conditional_fields=[...]` so you can check at a glance.

---

## 1. Page-shell & always-on shape

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 1.1 | `/` | Renders `Home`. Greeting shows shared `Brandon (goalie)` from `share()` middleware, plus library version. | `page-shell: component='Home' url='/' prop_keys=['app_name', 'errors', 'user', 'version'] conditional_fields=[]` |
| 1.2 | `view-source:http://localhost:8000/` | First-load shell is `<script data-page="app" type="application/json">…</script>` followed by `<div id="app"></div>`. **No** legacy `<div id="app" data-page="…">` form. | `first-load shell: rendering inline JSON for component='Home'` |
| 1.3 | Inspect the page-shell JSON | `props.errors` is `{}` (auto-injected). Conditional fields (`encryptHistory`, `clearHistory`, `preserveFragment`, `deferredProps`, `onceProps`, …) are **absent** unless the view opts in. | `conditional_fields=[]` |
| 1.4 | (Optional XSS canary) Temporarily add `motto="<script>alert(1)</script>"` to `share()` in `sample/apps/core/middleware.py`, reload `/`, grep page source for `<`. Remove canary after the check. | Page source contains `<script>alert(1)</script>`, never raw `<script>`. | `first-load shell: rendering inline JSON for component='Home' (raw_len=…, escaped_chars_added=30)` — the `escaped_chars_added` figure jumps from baseline 5 (just the `/` in `"url"`) to ~30 once `<`, `>`, `&` are present. |

---

## 2. Optional / defer / once / partial-data / partial-except / reset

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 2.1 | `/lazy/` initial visit (inspect raw HTML, `view-source:`) | Page-shell JSON has props `name`, `plans` (once), `topic` (once + fresh) — `sport`, `team`, `grit` are **absent** because they're `IgnoreOnFirstLoadProp`. `deferredProps: {"default": ["team"], "extras": ["grit"]}`. `onceProps` has two entries: `plans` (auto key, `expiresAt` numeric because `expires_in=timedelta(minutes=5)`) and `lazy-topic-v1` (custom `key=`, `prop: "topic"`, `expiresAt: null`). | `dropping prop 'sport' on first load (IgnoreOnFirstLoad: OptionalProp)` · `dropping prop 'team' on first load (IgnoreOnFirstLoad: DeferredProp)` · `dropping prop 'grit' on first load (IgnoreOnFirstLoad: DeferredProp)` · `emitting deferredProps={'default': ['team'], 'extras': ['grit']}` · `emitting onceProps={'plans': …, 'lazy-topic-v1': …}` |
| 2.1b | Same page, observe network | The v3 client immediately fires **one partial-data fetch per deferred group** in parallel (`X-Inertia-Partial-Data: team` and `X-Inertia-Partial-Data: grit`). Each carries `X-Inertia-Except-Once-Props: plans,lazy-topic-v1` automatically. After both resolve, the UI shows `team` and `grit`. | Two `build_props: … is_partial=True partial_data=['team'] … except_once=['plans', 'lazy-topic-v1']` and `… partial_data=['grit'] … except_once=['plans', 'lazy-topic-v1']` records. Each followed by `suppressing deferredProps on partial render of component='Lazy'`. |
| 2.2 | Click "Load `sport` (optional)" | Request: `X-Inertia-Partial-Data: sport`, `X-Inertia-Partial-Component: Lazy`. Response `props` contains `sport` and `errors` only. | `build_props: … is_partial=True partial_data=['sport'] …` plus six `dropping prop … because it is not in X-Inertia-Partial-Data` lines. |
| 2.3 | Click "Load `team` + `grit` (deferred)" | Request: `X-Inertia-Partial-Data: team,grit` (a single fetch — manual `router.reload` does not split per group). | `build_props: … partial_data=['team', 'grit'] …` (one record, not two). |
| 2.4 | Click "Reload `extras` group only" | Request: `X-Inertia-Partial-Data: grit`. Response includes `grit`; `team` (default group) is untouched in the UI. | `build_props: … partial_data=['grit'] …` |
| 2.5 | Click "Reset `plans` (once)" | Request: `X-Inertia-Partial-Data: plans` + `X-Inertia-Reset: plans`. Response `props.plans` resolves (because `plans` is in `X-Inertia-Partial-Data`, overriding the except-once header), but the **`onceProps` registry entry for `plans` is dropped** by the reset header — `conditional_fields` list does **not** include `onceProps`. The client treats the dropped registry as "evict your cached entry". | `once prop 'plans' (registry key='plans') survives X-Inertia-Except-Once-Props because it is in X-Inertia-Partial-Data` · `dropping once registry entry for 'plans' because it is in X-Inertia-Reset` |
| 2.6 | Click "Reload except `name`" | Request: `X-Inertia-Partial-Except: name` (the v3 client does **not** also send `X-Inertia-Partial-Data`). Response `props` contains every prop **except** `name` and `plans` — `name` is dropped by the except header, `plans` is dropped by the auto-sent `X-Inertia-Except-Once-Props` (see note ↓). `topic` is **kept** because `fresh=True` bypasses except-once. `errors` is still present (always-included). `deferredProps` is **absent** (server recognizes the request as a partial render off the component header alone, matching Laravel's `PropsResolver`). | `build_props: … is_partial=True partial_data=[] partial_except=['name'] except_once=['plans', 'lazy-topic-v1']` · `dropping prop 'name' because it is in X-Inertia-Partial-Except` · `skipping once prop 'plans' (registry key='plans') because it is in X-Inertia-Except-Once-Props` · `once prop 'topic' (registry key='lazy-topic-v1') survives X-Inertia-Except-Once-Props because fresh=True` · `suppressing deferredProps on partial render of component='Lazy'` |
| 2.7 | Hard-reload `/lazy/` to seed once-cache. Then `/lazy/` → `/` → `/lazy/` via `Link`. | First hop request `/` carries `X-Inertia-Except-Once-Props: plans,lazy-topic-v1` (the v3 client tells the server which once keys it has cached). On the back-hop, the v3 client **clears** its once cache when it receives a response from a different component, so the second `/lazy/` Link visit arrives with no except-once header — and the server emits `onceProps` again as a fresh first-load on that route. | First hop: `build_props: component='Home' … except_once=['plans', 'lazy-topic-v1']`. Back hop: `build_props: component='Lazy' is_partial=False … except_once=[]` followed by full `emitting onceProps=…`. |

---

## 3. Merge family + match_on

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 3.1 | `/lists/` initial visit (inspect raw HTML) | `users`, `notifications`, `filters` are in `props`. `recent_orders` is **missing from `props`** (deferred). Page-shell has `mergeProps: ["users", "recent_orders"]`, `prependProps: ["notifications"]`, `deepMergeProps: ["filters"]`, and `matchPropsOn` containing `users.id`, `notifications.id`, `filters.buckets.id`, `recent_orders.id`. The merge metadata for a deferred-merge prop is registered in the **first-load shell**, *before* the deferred fetch resolves — that's the v3 contract: register up front, populate later. `deferredProps.default` lists `recent_orders`. | `build_merge_kinds: mergeProps=['users', 'recent_orders'] prependProps=['notifications'] deepMergeProps=['filters'] matchPropsOn=['users.id', 'notifications.id', 'filters.buckets.id', 'recent_orders.id']` · `emitting deferredProps={'default': ['recent_orders']}` |
| 3.1b | Same page, observe network | The v3 client immediately fires `X-Inertia-Partial-Data: recent_orders` to resolve the deferred prop. `props.recent_orders` populates; the UI now shows the orders. | `build_props: … is_partial=True partial_data=['recent_orders'] …` · `build_merge_kinds: mergeProps=['recent_orders'] … matchPropsOn=['recent_orders.id']` |
| 3.2 | Click "Load `recent_orders` (deferred + merge)" | Manually re-trigger the same partial fetch. Response includes `recent_orders` and keeps it in `mergeProps`. | Same shape as 3.1b. |
| 3.3 | Click "Refresh users" | Partial reload of `users` only. Response keeps `users` in `mergeProps` and `users.id` in `matchPropsOn`. | `build_merge_kinds: mergeProps=['users'] … matchPropsOn=['users.id']` |
| 3.4 | Click "Reset users" | Request: `X-Inertia-Partial-Data: users` + `X-Inertia-Reset: users`. Response page-shell **omits** `mergeProps` / `prependProps` / `deepMergeProps` / `matchPropsOn` for that scope (`conditional_fields=[]`). That's how the server tells the client to drop the merged collection. | `dropping merge metadata for 'users' because it is in X-Inertia-Reset` · `conditional_fields=[]` |

---

## 4. Infinite scroll

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 4.1 | `/feed/` initial | Five items (`Item 10`–`Item 14`). Page-shell has `scrollProps.items = {pageName: "page", previousPage: null, nextPage: 2, currentPage: 1, reset: false}`. `mergeProps` contains `items`. `matchPropsOn` includes `items.id`. | `InfiniteScrollProp: X-Inertia-Infinite-Scroll-Merge-Intent='' → strategy=append` · `build_scroll_props: emitting scrollProps={'items': {'pageName': 'page', 'previousPage': None, 'nextPage': 2, 'currentPage': 1, 'reset': False}}` |
| 4.2 | Click "Load next page (append)" | Request: `?page=2`, no merge-intent header. Response: items **append**. `scrollProps.items` updates to `previousPage: 1, currentPage: 2, nextPage: 3`. `items` stays in `mergeProps`. | `InfiniteScrollProp: … intent='' → strategy=append` · `scrollProps={'items': {'pageName': 'page', 'previousPage': 1, 'nextPage': 3, 'currentPage': 2, 'reset': False}}` |
| 4.3 | Click "Load older (prepend)" | Request header `X-Inertia-Infinite-Scroll-Merge-Intent: prepend`. Response page-shell lists `items` in **`prependProps`**, **not** `mergeProps`. The list prepends. | `InfiniteScrollProp: X-Inertia-Infinite-Scroll-Merge-Intent='prepend' → strategy=prepend` · `build_merge_kinds: mergeProps=[] prependProps=['items'] …` |
| 4.4 | Click "Reset feed" | Request: `X-Inertia-Partial-Data: items` + `X-Inertia-Reset: items`. Response `scrollProps.items.reset === true`. `mergeProps`, `prependProps`, and `matchPropsOn` are all absent — server signals client-side reset. | `dropping merge metadata for 'items' because it is in X-Inertia-Reset` · `scrollProps={'items': {…, 'reset': True}}` · `conditional_fields=['scrollProps']` |

---

## 5. useForm validation (Inertia-native flow)

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 5.1 | `/form/` submit empty | UI stays on the form. Errors render inline (`Name is required`, `Email is invalid`). Network: response is a normal **Inertia 200** with component `Form`; JSON has `props.errors = {name, email}`. **Address-bar URL becomes `/form/submit/`** because Inertia takes the URL of the 200 response — that is expected. | `middleware: method=POST path='/form/submit/' is_inertia=True downstream_status=200` · `page-shell: component='Form' url='/form/submit/' prop_keys=['app_name', 'errors', 'user'] conditional_fields=[]` |
| 5.2 | `/form/` submit valid `{name: "x", email: "x@y"}` | Server returns 302 → `/?submitted=1`; v3 client follows. Lands on `Home`. The middleware does **not** convert the 302 to 303 here (POST is exempt from the v3 method-conversion contract). | `POST /form/submit/ HTTP/1.1" 302` (Django access log) followed by `middleware: method=GET path='/?submitted=1' is_inertia=True downstream_status=200` |

---

## 6. errors_response / useHttp validation flow

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 6.1 | `/validate/` submit empty `name` | Plain XHR `POST /api/validate/` with `Content-Type: application/json` and `X-CSRFToken`. Response is **422 JSON**: `{"message": "The given data was invalid.", "errors": {"name": "Name is required"}}`. **No** Inertia visit happens. UI renders the error inline. The browser logs `Failed to load resource: the server responded with a status of 422` in the console — Chrome's default for non-2xx XHR, not an application error. | `errors_response(): status=422 fields=['name'] message='The given data was invalid.'` · `middleware: method=POST path='/api/validate/' is_inertia=False downstream_status=422` |
| 6.2 | `/validate/` submit `name: "ok"` | Response `200 {"ok": true}`. UI shows "OK (200)". | `middleware: method=POST path='/api/validate/' is_inertia=False downstream_status=200` (no `errors_response()` line — the helper isn't called on the success path) |
| 6.3 | Compare with section 5 | Section 5's response is a 200 Inertia page. Section 6's is a 422 JSON. The library exposes both flows by design — `useForm` for full Inertia visits, `errors_response` for `useHttp`-style XHR. | n/a |

---

## 7. Redirects

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 7.1 | Click `inertia_redirect()` link → `/inertia-redirect/` | Server returns **409** with `X-Inertia-Redirect: /lists/`. v3 client navigates to `/lists/` without a hard reload. | `inertia_redirect(): emitting 409 with X-Inertia-Redirect='/lists/'` · `middleware: method=GET path='/inertia-redirect/' is_inertia=True downstream_status=409` |
| 7.2 | Click `location()` link → `/location/` | Server returns **409** with `X-Inertia-Location: https://example.com/`. v3 client performs a **hard** browser navigation to `https://example.com/`. (If example.com is unreachable the browser shows a `chromewebdata` error — that's the redirect happening, not a library bug.) Use the back button to return. | `location(): emitting 409 with X-Inertia-Location='https://example.com/'` · `middleware: method=GET path='/location/' is_inertia=True downstream_status=409` |
| 7.3 | Click `Fragment redirect (middleware)` link → `/redirect-fragment/` | Server view returns plain `redirect("/lists/#users")` (a 302). **InertiaMiddleware** intercepts on the Inertia request and rewrites to `409 + X-Inertia-Redirect: /lists/#users`. Final URL: `/lists/#users`. | `middleware: fragment redirect detected (status=302, location='/lists/#users') → rewriting to 409 X-Inertia-Redirect` · `inertia_redirect(): emitting 409 with X-Inertia-Redirect='/lists/#users'` |
| 7.4 | Click `preserve_fragment` link `<Link href="/preserve-fragment/#users">` | The view calls `preserve_fragment(request)` then `redirect("/lists/")` (no fragment in `Location`). The follow-up `/lists/` Inertia response includes **`preserveFragment: true`**. v3 client carries the original `#users` fragment to `/lists/`. Final URL: `/lists/#users`. | `preserve_fragment(): set session flash flag (one-shot)` · `page-shell: emitting preserveFragment=True for component='Lists' (one-shot session flash consumed)` |

> **Note** — `Home.tsx` wraps each of these as `<Link>`. If you change one to a plain `<a>`, the v3 client never injects the `X-Inertia` header and the InertiaMiddleware path is silently skipped (the browser falls back to native redirect handling). The middleware DEBUG log line `is_inertia=False` is the canary.

---

## 8. History controls

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 8.1 | `/history/` | Page-shell JSON contains `encryptHistory: true` (the view called `encrypt_history(request)`). `clearHistory` is absent. | `encrypt_history(): set request flag to True` · `page-shell: emitting encryptHistory=True for component='History'` · `conditional_fields=['encryptHistory']` |
| 8.2 | Click "Clear history (server-flash → redirect)" → `/clear-history/` | Server stamps a session flag and 302s to `/history-after-clear/`. The follow-up `History` response contains `clearHistory: true`. | `clear_history(): set session flash flag (one-shot)` · `page-shell: emitting clearHistory=True for component='History' (one-shot session flash consumed)` |
| 8.3 | Reload `/history-after-clear/` directly | `clearHistory` is **absent** — the session flash is one-shot. | `page-shell: component='History' url='/history-after-clear/' prop_keys=['app_name', 'errors', 'note', 'user'] conditional_fields=[]` (no `clearHistory` line) |

---

## 9. Method conversion (303 on PUT/PATCH/DELETE redirects)

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 9.1 | `/method/` click "PUT /method/submit/" | XHR is `PUT`. Server view returns 302 to `/?method=put`; **InertiaMiddleware** converts the response status to **303** (per the v3 protocol). v3 client follows the 303 with a `GET` and lands on `Home`. | `middleware: converting PUT redirect from 302 to 303 (per v3 method-conversion contract)` |
| 9.2 | Same with PATCH | Final URL: `/?method=patch`. Status on the redirect response is **303**. | `middleware: converting PATCH redirect from 302 to 303 (per v3 method-conversion contract)` |
| 9.3 | Same with DELETE | Final URL: `/?method=delete`. Status on the redirect response is **303**. | `middleware: converting DELETE redirect from 302 to 303 (per v3 method-conversion contract)` |

---

## 10. Stale version refresh

The library compares the request's `X-Inertia-Version` against `INERTIA_VERSION`. A mismatch on an Inertia request triggers a hard reload (so the SPA gets a fresh asset bundle).

| Step | URL / action | Expected (network + DOM) | Expected log substring |
|------|--------------|--------------------------|------------------------|
| 10.1 | Stop Django. Restart with `INERTIA_VERSION=2.0 python -u manage.py runserver --noreload 0.0.0.0:8000`. | Server now advertises `version: "2.0"` in fresh page-shells. | n/a |
| 10.2 | Open a new tab on `/` to seed a v2 client. Then in the seeded tab navigate via `Link` to any other route. | Request carries `X-Inertia-Version: 2.0` matching server — normal navigation. | `middleware: method=GET path=… is_inertia=True downstream_status=200` (no stale-version line) |
| 10.3 | Without restarting the seeded tab, restart the server with `INERTIA_VERSION=3.0`. | Server now advertises `3.0`; the seeded tab still thinks `2.0`. | n/a |
| 10.4 | In the seeded tab, click any `Link` | Server responds **409 + `X-Inertia-Location: <full URL>`**. v3 client performs a hard reload, which fetches a fresh page-shell with `version: "3.0"`. | `middleware: stale version (client='2.0', server='3.0') → 409 X-Inertia-Location for hard reload` · `location(): emitting 409 with X-Inertia-Location='http://localhost:8000/…'` |
| 10.5 | Restart Django with default (`INERTIA_VERSION=1.0`) for the rest of the checklist. | Standard navigation resumes. | n/a |

---

## Cross-cutting assertions to watch for

These are not separate steps — verify them while running the checklist.

- **Page-shell.** `<script data-page="app" type="application/json">…</script>` followed by `<div id="app"></div>`. The v3 client refuses to boot from the legacy `<div id="app" data-page="…">` form. Log: `first-load shell: rendering inline JSON for component=…`.
- **JSON escape.** Any `<`, `>`, `&`, `/` inside the page-shell JSON is escaped to `<`, `>`, `&`, `/`. Section 1.4 has the canary check. Log: every first-load reports `escaped_chars_added=N` — the figure is non-zero on every run because URLs in the JSON contain `/`.
- **Always-included `errors`.** Every Inertia response carries `props.errors`. It survives `X-Inertia-Partial-Data` filtering. It is removed only when explicitly listed in `X-Inertia-Partial-Except` — and the library logs `dropping always-included prop 'errors'` when that happens.
- **Only-when-true emission.** `encryptHistory`, `clearHistory`, `preserveFragment` are absent unless `true` (v3 spec). The page-shell log line's `conditional_fields=[…]` enumerates exactly which made it into the response.
- **CSRF.** Every XHR — Inertia visits via `useForm`/`router.*` and `useHttp`-style XHRs in section 6 — carries `X-CSRFToken` sourced from the `csrftoken` cookie. Django returns 403 if missing.
- **No console errors.** v3 client throws fast on a malformed page-shell. Any "Cannot read properties of null (reading 'component')" on first load means the JSON `<script>` tag isn't reaching the browser.
- **Response status codes.** 200 for normal Inertia visits; 409 for `inertia_redirect` / `location` / fragment-redirect / stale-version; 303 for non-POST redirects (section 9); 422 for `errors_response` (section 6).

---

## Where the DEBUG logs come from

Every entry in the **Expected log substring** column above is emitted by `inertia_django_full_of_juice` from these call sites:

- `inertia/http.py` — `BaseInertiaResponseMixin.page_data` / `build_props` / `build_once_props` / `build_deferred_props` / `build_merge_kinds` / `build_scroll_props` / `build_first_load_context_and_template`, plus the standalone `location()`, `inertia_redirect()`, `errors_response()`, `encrypt_history()`, `clear_history()`, `preserve_fragment()` helpers.
- `inertia/middleware.py` — `InertiaMiddleware.__call__` (one summary record per request, plus per-decision records for fragment-redirect rewrite, 302→303 method conversion, stale-version refresh).
- `inertia/infinite_scroll.py` — `InfiniteScrollProp.merge_strategy()` logs the resolved intent.

Library tests in `inertia/tests/test_logging.py` assert the exact phrasing of every log line, so the substrings above are a stable contract — they shouldn't drift with refactors.

---

## Notes on running the canary checks

- **XSS escape canary (section 1.4) is best-effort.** The library escapes `<`, `>`, `&`, and `/` in the page-shell JSON (`inertia/http.py:475` and the surrounding helper). A clean response body has no `<`/`>`/`&` to escape, so a plain run won't prove it. The `/` escape *is* observable on every run because every page-shell contains URL/path strings (e.g. `"url": "/"`); the `escaped_chars_added=…` figure in the first-load log is `5` on `/` and goes up from there. To exercise `<`, `>`, `&`: temporarily edit `sample/apps/core/middleware.py` `ShareDemoMiddleware` to inject `motto="<script>alert(1)</script>"`, reload `/`, grep page source for `<`. The same first-load log will then report `escaped_chars_added=30`.

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
