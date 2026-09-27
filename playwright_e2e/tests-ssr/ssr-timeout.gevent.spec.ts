import { expect, test } from "@playwright/test";

/**
 * Runs against the `with-ssr-gevent` service (:8002): gunicorn's gevent worker
 * with a per-request `gevent.Timeout` deadline of 20s (raising an `Exception`
 * subclass, see `sample_project/gunicorn_gevent.py`), SSR enabled and pointed
 * at a stub that accepts connections and never answers, and
 * INERTIA_SSR_TIMEOUT=1.
 *
 * Without the timeout the render call would wait for the 20s deadline; the
 * spec proves it is bounded by INERTIA_SSR_TIMEOUT instead, that the waiting
 * render yields to other requests, and that a deadline firing mid-render
 * reaches the application instead of being swallowed into a 200 shell.
 */

const CLIENT_SHELL = '<script data-page="app" type="application/json">';

test.describe("SSR render timeout under gunicorn + gevent (INERTIA_SSR_TIMEOUT)", () => {
	test("a hung SSR service falls back to the client shell within the timeout", async ({
		request,
	}) => {
		const started = Date.now();
		const response = await request.get("/");
		const elapsed = Date.now() - started;

		expect(response.status()).toBe(200);
		const html = await response.text();
		expect(html).toContain(CLIENT_SHELL);
		expect(html).not.toContain('data-server-rendered="true"');
		// The render call really waited on the hung stub (≈1s)...
		expect(elapsed).toBeGreaterThanOrEqual(900);
		// ...and was cut off by INERTIA_SSR_TIMEOUT, not the 20s deadline.
		expect(elapsed).toBeLessThan(8_000);
	});

	test("the fallback page still renders in the browser", async ({ page }) => {
		await page.goto("/");

		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample" }),
		).toBeVisible();
	});

	test("a render call waiting on the SSR service does not block the worker", async ({
		request,
	}) => {
		// One gevent worker process. While a first load waits ~1s on the hung
		// stub, an Inertia visit (which never calls SSR) must be served at once.
		const delayMs = 500;
		const ssrTimeoutMs = 1_000;
		let firstLoadDone = false;
		const started = Date.now();
		const firstLoad = request.get("/").then((response) => {
			firstLoadDone = true;
			return { response, elapsed: Date.now() - started };
		});
		await new Promise((resolve) => setTimeout(resolve, delayMs));

		const visitStarted = Date.now();
		const visit = await request.get("/", {
			// INERTIA_VERSION is unset on this service, so the sample serves "1.0".
			headers: { "X-Inertia": "true", "X-Inertia-Version": "1.0" },
		});
		const visitElapsed = Date.now() - visitStarted;

		expect(visit.status()).toBe(200);
		expect((await visit.json()).component).toBe("Home");
		expect(firstLoadDone).toBe(false);
		const first = await firstLoad;
		expect(first.response.status()).toBe(200);
		// Proof of overlap: the render call waits at least the SSR timeout from
		// the moment the first load reaches the server. Had it only arrived after
		// the visit was served, it could not finish before this bound.
		expect(first.elapsed).toBeLessThan(delayMs + visitElapsed + ssrTimeoutMs);
	});

	test("a request deadline firing during the render call is not swallowed", async ({
		request,
	}) => {
		// Shorten this request's deadline to 0.3s so it fires while the render
		// call is still waiting (INERTIA_SSR_TIMEOUT=1s). The deadline must
		// reach Django as a 500, not be turned into a 200 client shell.
		const response = await request.get("/", {
			headers: { "X-E2E-Request-Deadline": "0.3" },
		});

		expect(response.status()).toBe(500);
		const html = await response.text();
		expect(html).not.toContain(CLIENT_SHELL);
		// DEBUG=True on this service: the technical 500 page names the error and
		// its traceback, which must run through the SSR render call — proof the
		// deadline fired while the call was waiting, not before it.
		expect(html).toContain("RequestDeadlineExceededError");
		expect(html).toContain("build_first_load_context_and_template");
	});
});
