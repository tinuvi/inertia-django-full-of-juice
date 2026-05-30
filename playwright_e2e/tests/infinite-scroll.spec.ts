import { expect, test } from "@playwright/test";

test.describe("Feed — infinite_scroll", () => {
	test("appends the next page onto the existing items", async ({ page }) => {
		await page.goto("/feed/");
		await expect(page.getByRole("heading", { name: /Feed/ })).toBeVisible();

		// page 1 → Item 10..14
		await expect(page.getByText("Item 10", { exact: true })).toBeVisible();
		await expect(page.getByText("Item 14", { exact: true })).toBeVisible();
		await expect(page.getByText("Item 20", { exact: true })).toHaveCount(0);

		// append page 2 → Item 20..24 merge in, page 1 retained
		await page.getByRole("button", { name: /Load next page/ }).click();
		await expect(page.getByText("Item 20", { exact: true })).toBeVisible();
		await expect(page.getByText("Item 10", { exact: true })).toBeVisible();
	});

	test("reset signals a scroll reset in the response", async ({ page }) => {
		await page.goto("/feed/");
		await expect(page.getByText("Item 10", { exact: true })).toBeVisible();

		// Reset is a server-signaled behavior (scrollProps.items.reset === true);
		// the client decides what to do with it, so assert the wire signal.
		const reset = page.waitForResponse((r) => {
			const resetHeader = r.request().headers()["x-inertia-reset"] ?? "";
			return r.url().includes("/feed/") && resetHeader.includes("items");
		});
		await page.getByRole("button", { name: /Reset feed/ }).click();
		const pageObject = await (await reset).json();

		expect(pageObject.scrollProps.items.reset).toBe(true);
	});

	test("prepend intent keeps the existing items", async ({ page }) => {
		await page.goto("/feed/");
		await expect(page.getByText("Item 10", { exact: true })).toBeVisible();

		await page.getByRole("button", { name: /Load older \(prepend\)/ }).click();

		// prepend re-sends page 1 (match_on=id dedupes) — the list stays intact.
		await expect(page.getByText("Item 10", { exact: true })).toBeVisible();
		await expect(page.getByText("Item 14", { exact: true })).toBeVisible();
	});
});
