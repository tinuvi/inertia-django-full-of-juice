import { expect, test } from "@playwright/test";

test.describe("Asset versioning (INERTIA_VERSION)", () => {
	test("page-shell JSON carries the configured asset version as a string", async ({
		request,
	}) => {
		const html = await (await request.get("/")).text();
		const match = html.match(
			/<script data-page="app" type="application\/json">(.*?)<\/script>/s,
		);
		expect(match, "page-shell <script> not found").not.toBeNull();

		const page = JSON.parse((match as RegExpMatchArray)[1]);
		// resolve_inertia_version() casts INERTIA_VERSION to a string; the sample
		// app leaves it at the "1.0" default.
		expect(page.version).toBe("1.0");
	});

	test("client echoes the version in X-Inertia-Version on a client-side visit", async ({
		page,
	}) => {
		await page.goto("/");

		const [navRequest] = await Promise.all([
			page.waitForRequest(
				(req) =>
					req.headers()["x-inertia"] === "true" &&
					new URL(req.url()).pathname === "/lists/",
			),
			page.getByRole("link", { name: /^Lists/ }).click(),
		]);

		// The v3 client only sends X-Inertia-Version when page.version is truthy,
		// and echoes it verbatim. It must match the shell's resolved version so the
		// server treats the request as fresh (no 409 hard reload).
		expect(navRequest.headers()["x-inertia-version"]).toBe("1.0");
	});

	test("stale X-Inertia-Version on a GET returns 409 + X-Inertia-Location", async ({
		request,
		baseURL,
	}) => {
		const response = await request.get("/", {
			headers: {
				"X-Inertia": "true",
				"X-Inertia-Version": "stale-version",
			},
		});

		// InertiaMiddleware compares X-Inertia-Version against the resolved
		// server version on every Inertia GET; a mismatch short-circuits into a
		// 409 whose X-Inertia-Location carries the absolute URL to hard-reload.
		expect(response.status()).toBe(409);
		expect(response.headers()["x-inertia-location"]).toBe(`${baseURL}/`);
	});

	test("a stale client recovers via a full hard reload", async ({ page }) => {
		await page.goto("/");
		await page.evaluate(() => {
			(window as unknown as { __noReload: boolean }).__noReload = true;
		});

		// Force staleness on the first Inertia visit only: Lists fires a
		// deferred-prop fetch right after the hard reload, and rewriting that
		// one too would loop the client through endless 409 reloads.
		let staleSent = false;
		await page.route("**/lists/", async (route) => {
			const headers = { ...route.request().headers() };
			if (!staleSent && headers["x-inertia"]) {
				staleSent = true;
				headers["x-inertia-version"] = "stale-version";
			}
			await route.continue({ headers });
		});

		await page.getByRole("link", { name: /^Lists/ }).click();

		// The 409 + X-Inertia-Location makes the client abandon the XHR visit
		// and re-request /lists/ as a full document load — the in-memory marker
		// is gone once the new document boots. (waitForFunction survives the
		// navigation, unlike a bare evaluate.)
		await page.waitForFunction(
			() =>
				(window as unknown as { __noReload?: boolean }).__noReload ===
				undefined,
		);
		await expect(page).toHaveURL(/\/lists\/$/);
		await expect(
			page.getByRole("heading", { name: "List props", level: 1 }),
		).toBeVisible();
	});
});
