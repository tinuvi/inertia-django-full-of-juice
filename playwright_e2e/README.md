# Playwright E2E

End-to-end tests for `inertia-django-full-of-juice`, driven through the dockerized sample
project against real Django + Vite + React (Inertia v3) renders. These are the regression
guard for the v3 protocol surfaces in CI (`.github/workflows/playwright.yml`).

The suite runs against two Django configurations brought up by
`sample_project/docker-compose.yml`:

| Project       | URL                     | Config                                            | Specs        |
|---------------|-------------------------|---------------------------------------------------|--------------|
| `without-ssr` | `http://localhost:8000` | SSR disabled                                      | `tests/`     |
| `with-ssr`    | `http://localhost:8001` | SSR enabled, `INERTIA_SSR_EXCLUDE=^/lists/`       | `tests-ssr/` |

## Running

From the repo root, bring up the sample stack, then run the suite from here:

```bash
# 1. Start the dockerized sample (both web variants + the SSR sidecar)
docker compose -f sample_project/docker-compose.yml up --build -d --wait

# 2. Install and run
cd playwright_e2e
npm ci
npm run install-browsers     # first run only: downloads Chromium + OS deps
npm run test                 # without-ssr project (:8000)
npm run test:ssr             # with-ssr project (:8001)
npm run test:all             # both projects

# 3. Tear down
docker compose -f sample_project/docker-compose.yml down -v --remove-orphans
```

`WITHOUT_SSR_URL` / `WITH_SSR_URL` override the target base URLs (defaults shown above).
