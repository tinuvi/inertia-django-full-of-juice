import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests for `inertia-django-full-of-juice`, run against the
 * dockerized sample project (see `sample_project/docker-compose.yml`).
 *
 * Three Playwright projects, one per Django configuration the compose stack
 * brings up — there is no `webServer`, the stack provides the servers:
 *   - `without-ssr`     → http://localhost:8000  (SSR disabled)
 *   - `with-ssr`        → http://localhost:8001  (SSR enabled, INERTIA_SSR_EXCLUDE=^/lists/)
 *   - `with-ssr-gevent` → http://localhost:8002  (gunicorn + gevent, SSR pointed
 *                         at a hung stub, INERTIA_SSR_TIMEOUT=1). Runs the
 *                         `tests-ssr/*.gevent.spec.ts` files; `with-ssr` skips them.
 *
 * Bring the stack up first (`docker compose -f sample_project/docker-compose.yml
 * up --build -d --wait`), then `npm run test` / `npm run test:ssr` (both SSR projects).
 */

const WITHOUT_SSR_URL = process.env.WITHOUT_SSR_URL ?? "http://localhost:8000";
const WITH_SSR_URL = process.env.WITH_SSR_URL ?? "http://localhost:8001";
const WITH_SSR_GEVENT_URL =
	process.env.WITH_SSR_GEVENT_URL ?? "http://localhost:8002";
const GEVENT_SPECS = "**/*.gevent.spec.ts";
const isCI = !!process.env.CI;

export default defineConfig({
	fullyParallel: false,
	workers: 1,
	forbidOnly: isCI,
	retries: isCI ? 2 : 0,
	timeout: 60_000,
	expect: { timeout: 15_000 },
	reporter: isCI
		? [["github"], ["html", { open: "never" }]]
		: [["list"], ["html", { open: "never" }]],
	use: {
		trace: "on-first-retry",
		screenshot: "only-on-failure",
	},
	projects: [
		{
			name: "without-ssr",
			testDir: "./tests",
			use: { ...devices["Desktop Chrome"], baseURL: WITHOUT_SSR_URL },
		},
		{
			name: "with-ssr",
			testDir: "./tests-ssr",
			testIgnore: GEVENT_SPECS,
			use: { ...devices["Desktop Chrome"], baseURL: WITH_SSR_URL },
		},
		{
			name: "with-ssr-gevent",
			testDir: "./tests-ssr",
			testMatch: GEVENT_SPECS,
			use: { ...devices["Desktop Chrome"], baseURL: WITH_SSR_GEVENT_URL },
		},
	],
});
