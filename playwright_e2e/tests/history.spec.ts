import { expect, test } from "@playwright/test";

test.describe("History controls", () => {
	test("encrypt_history() sets encryptHistory on the page", async ({
		page,
	}) => {
		await page.goto("/history/");

		await expect(
			page.getByRole("heading", { name: "History controls" }),
		).toBeVisible();
		// The History page surfaces the page-object boolean directly in the DOM.
		await expect(
			page.locator("li", { hasText: "encryptHistory" }),
		).toContainText("true");
	});

	test("clear_history() flashes clearHistory on the next response", async ({
		page,
	}) => {
		await page.goto("/history/");

		// Plain <a> → full navigation to /clear-history/, which redirects to
		// /history-after-clear/ where the one-shot clearHistory flash is consumed.
		await page.getByRole("link", { name: /Clear history/ }).click();

		await expect(page).toHaveURL(/\/history-after-clear\/$/);
		await expect(
			page.locator("li", { hasText: "clearHistory" }),
		).toContainText("true");
	});
});
