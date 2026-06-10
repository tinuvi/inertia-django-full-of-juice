import { expect, test } from "@playwright/test";

test.describe("Lazy — deferred & optional props", () => {
	test("resolves deferred props after the first load", async ({ page }) => {
		await page.goto("/lazy/");

		await expect(
			page.getByRole("heading", { name: "Lazy props" }),
		).toBeVisible();

		const pre = page.locator("pre");
		await expect(pre).toContainText('"name": "Brian"');

		// `team` (default group) and `grit` (extras group) are deferred — the v3
		// client fires one partial fetch per group and they populate shortly.
		await expect(pre).toContainText('"team": "Bulls"');
		await expect(pre).toContainText('"grit": "intense"');
	});

	test("page shell declares one deferredProps entry per group", async ({
		request,
	}) => {
		const html = await (await request.get("/lazy/")).text();
		const match = html.match(
			/<script data-page="app" type="application\/json">(.*?)<\/script>/s,
		);
		expect(match, "page-shell <script> not found").not.toBeNull();

		const page = JSON.parse((match as RegExpMatchArray)[1]);
		// The registry is keyed by group: `team` has no group (→ "default"),
		// `grit` opts into "extras". This is what drives the per-group fetches.
		expect(page.deferredProps).toEqual({
			default: ["team"],
			extras: ["grit"],
		});
	});

	test("fires one parallel partial fetch per deferred group", async ({
		page,
	}) => {
		const partialFetches: string[] = [];
		page.on("request", (req) => {
			const partialData = req.headers()["x-inertia-partial-data"];
			if (new URL(req.url()).pathname === "/lazy/" && partialData) {
				partialFetches.push(partialData);
			}
		});

		await page.goto("/lazy/");

		const pre = page.locator("pre");
		await expect(pre).toContainText('"team": "Bulls"');
		await expect(pre).toContainText('"grit": "intense"');

		// Two groups → exactly two partial reloads, each scoped via
		// X-Inertia-Partial-Data to its own group's props.
		expect(partialFetches.sort()).toEqual(["grit", "team"]);
	});

	test("loads an optional prop on demand via partial reload", async ({
		page,
	}) => {
		await page.goto("/lazy/");

		const pre = page.locator("pre");
		await expect(pre).toContainText('"name": "Brian"');

		// `sport` is optional() — it only resolves when explicitly requested.
		await page.getByRole("button", { name: /Load `sport`/ }).click();

		await expect(pre).toContainText('"sport": "Basketball"');
	});
});
