# E2E testing

Manual end-to-end regression checklist for the sample project. Run this whenever the library changes to confirm the v3 protocol surfaces still work.

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

Use `playwright-mcp` (e.g. via Claude Code) or any browser. Walk the routes below and assert what each one should do.

## Regression checklist

| Step | URL | Expected |
|------|-----|----------|
| 1 | `/` | Renders `Home` page; greeting shows shared user `Brandon (goalie)` and library version |
| 2 | `/lazy/` (initial) | `name`, `plans` (once), `team`, `grit` (deferred) all present; `sport` (optional) absent |
| 3 | Click "Load `sport`" | After partial reload, `sport: "Basketball"` appears alongside existing props |
| 4 | `/lists/` | `users` (merge), `notifications` (prepend), `filters` (deep_merge) all render |
| 5 | `/feed/` | Five items rendered (`Item 10`–`Item 14` for page 1) |
| 6 | `/form/` then submit empty | Stays on form; `Name is required` and `Email is invalid` errors render inline |
| 7 | `/form/` then submit valid data | Redirects to `/?submitted=1` and renders `Home` |
| 8 | `/redirect-fragment/` | Lands on `/lists/#users` (fragment preserved through Inertia 409 redirect) |

## What to watch for

- **No console errors.** v3 client throws fast on a malformed page-shell, so any "Cannot read properties of null" on first load means the JSON `<script>` tag isn't reaching the browser.
- **Network tab on partial reloads** (`/lazy/` step 3): request must include `X-Inertia-Partial-Data: sport` and `X-Inertia-Partial-Component: Lazy`; response is JSON with only `sport` resolved.
- **CSRF.** All POSTs must carry the `X-CSRFToken` header sourced from the `csrftoken` cookie. Django returns 403 if missing.
