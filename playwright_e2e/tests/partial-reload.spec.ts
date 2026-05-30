import { expect, test } from "@playwright/test";

test.describe("Lazy — partial reloads (data / except)", () => {
	test("reloading the extras group requests only grit", async ({ page }) => {
		await page.goto("/lazy/");
		await expect(page.locator("pre")).toContainText('"grit": "intense"');

		const reload = page.waitForResponse((r) => {
			const partialData = r.request().headers()["x-inertia-partial-data"] ?? "";
			return r.url().endsWith("/lazy/") && partialData === "grit";
		});
		await page
			.getByRole("button", { name: /Reload `extras` group only/ })
			.click();
		const pageObject = await (await reload).json();

		expect(Object.keys(pageObject.props)).toContain("grit");
		expect(Object.keys(pageObject.props)).not.toContain("team");
	});

	test("reload-except omits the excepted prop but keeps errors", async ({
		page,
	}) => {
		await page.goto("/lazy/");
		await expect(page.locator("pre")).toContainText('"name": "Brian"');

		const reload = page.waitForResponse((r) => {
			const except = r.request().headers()["x-inertia-partial-except"] ?? "";
			return r.url().endsWith("/lazy/") && except.includes("name");
		});
		await page.getByRole("button", { name: /Reload except `name`/ }).click();
		const pageObject = await (await reload).json();

		expect(Object.keys(pageObject.props)).not.toContain("name");
		// errors is always-included, even under X-Inertia-Partial-Except.
		expect(Object.keys(pageObject.props)).toContain("errors");
	});
});
