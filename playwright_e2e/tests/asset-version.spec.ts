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
});
