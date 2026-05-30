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
