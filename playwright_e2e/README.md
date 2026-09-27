# Playwright E2E

End-to-end tests for `inertia-django-full-of-juice`, driven through the dockerized sample
project against real Django + Vite + React (Inertia v3) renders. These are the regression
guard for the v3 protocol surfaces in CI (`.github/workflows/playwright.yml`).

The suite runs against three Django configurations brought up by
`sample_project/docker-compose.yml`:

| Project           | URL                     | Config                                                                                              | Specs                           |
|-------------------|-------------------------|-----------------------------------------------------------------------------------------------------|---------------------------------|
| `without-ssr`     | `http://localhost:8000` | SSR disabled                                                                                        | `tests/`                        |
| `with-ssr`        | `http://localhost:8001` | SSR enabled, `INERTIA_SSR_EXCLUDE=^/lists/`                                                         | `tests-ssr/` (not `*.gevent.*`) |
| `with-ssr-gevent` | `http://localhost:8002` | gunicorn + gevent worker, per-request `gevent.Timeout`, SSR at a hung stub, `INERTIA_SSR_TIMEOUT=1` | `tests-ssr/*.gevent.spec.ts`    |

## Running

From the repo root, bring up the sample stack, then run the suite from here:

```bash
# 1. Start the dockerized sample (the three web variants, the SSR sidecar and the hung SSR stub)
docker compose -f sample_project/docker-compose.yml up --build -d --wait

# 2. Install and run
cd playwright_e2e
npm ci
npm run install-browsers     # first run only: downloads Chromium + OS deps
npm run test                 # without-ssr project (:8000)
npm run test:ssr             # with-ssr (:8001) + with-ssr-gevent (:8002) projects
npm run test:all             # all projects

# 3. Tear down
docker compose -f sample_project/docker-compose.yml down -v --remove-orphans
```

`WITHOUT_SSR_URL` / `WITH_SSR_URL` / `WITH_SSR_GEVENT_URL` override the target base URLs (defaults shown above).
