import { expect, test } from "@playwright/test";

test.describe("Lists — merge / prepend / deep_merge / match_on", () => {
	test("renders every merge-family prop on first load", async ({ page }) => {
		await page.goto("/lists/");
		await expect(
			page.getByRole("heading", { name: "List props" }),
		).toBeVisible();

		const users = page.locator("pre").nth(0);
		await expect(users).toContainText("Brandon");
		await expect(users).toContainText("Brian");

		// notifications (prepend) and filters (deep_merge) render too.
		await expect(page.getByText("welcome back")).toBeVisible();
		await expect(page.getByText('"label": "Active"')).toBeVisible();

		// recent_orders is defer(merge=True) — it auto-resolves after first load.
		await expect(page.getByText('"total": "$10.00"')).toBeVisible();
	});

	test("partial reload keeps users registered as a merge prop with match_on", async ({
		page,
	}) => {
		await page.goto("/lists/");
		// let the deferred recent_orders fetch settle first.
		await expect(page.getByText('"total": "$10.00"')).toBeVisible();

		const reload = page.waitForResponse((r) => {
			const partialData = r.request().headers()["x-inertia-partial-data"] ?? "";
			return r.url().endsWith("/lists/") && partialData.includes("users");
		});
		await page.getByRole("button", { name: "Refresh users" }).click();
		const pageObject = await (await reload).json();

		expect(pageObject.mergeProps).toContain("users");
		expect(pageObject.matchPropsOn).toContain("users.id");
	});
});
