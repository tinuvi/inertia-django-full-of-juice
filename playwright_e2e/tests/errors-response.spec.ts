import { expect, test } from "@playwright/test";

test.describe("Validate — errors_response / useHttp (plain XHR)", () => {
	test("renders the 422 error inline on an empty submit", async ({ page }) => {
		await page.goto("/validate/");

		await page.getByRole("button", { name: /Submit \(plain XHR\)/ }).click();

		// /api/validate/ returns 422 {message, errors} — the page renders both.
		await expect(page.getByText("Name is required")).toBeVisible();
		await expect(page.getByText("The given data was invalid.")).toBeVisible();
	});

	test("shows OK on a valid submit", async ({ page }) => {
		await page.goto("/validate/");

		await page.getByLabel("Name").fill("ok");
		await page.getByRole("button", { name: /Submit \(plain XHR\)/ }).click();

		await expect(page.getByText("OK (200)")).toBeVisible();
	});
});
