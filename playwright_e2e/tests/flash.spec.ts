import { expect, test } from "@playwright/test";

test.describe("Flash native — the v3 flash page field", () => {
	test("flash(request, …) survives the redirect and rides the page object", async ({
		page,
	}) => {
		await page.goto("/flash-native/");

		const followUp = page.waitForResponse(
			(r) =>
				new URL(r.url()).pathname === "/flash-native/" &&
				r.request().method() === "GET",
		);
		await page.getByRole("button", { name: "Save" }).click();

		// The redirected-to render pulls the session flash into the page
		// object's top-level `flash` field (a sibling of props).
		const pageObject = await (await followUp).json();
		expect(pageObject.flash).toEqual({
			toast: { text: "Saved with the v3 flash field!", kind: "success" },
		});

		await expect(page.getByTestId("flash-toast")).toHaveText(
			"Saved with the v3 flash field!",
		);
	});

	test("the global flash event fires on responses carrying flash data", async ({
		page,
	}) => {
		await page.goto("/flash-native/");

		await page.getByRole("button", { name: "Save" }).click();

		await expect(page.getByTestId("flash-event-log")).toContainText(
			"event: Saved with the v3 flash field!",
		);
	});

	test("flash is one-shot: a fresh load after consumption has none", async ({
		page,
	}) => {
		await page.goto("/flash-native/");
		await page.getByRole("button", { name: "Save" }).click();
		await expect(page.getByTestId("flash-toast")).toBeVisible();

		await page.reload();

		await expect(page.getByTestId("flash-toast")).toHaveCount(0);
	});

	test("history restore never replays a flash (client strips it)", async ({
		page,
	}) => {
		await page.goto("/flash-native/");
		await page.getByRole("button", { name: "Save" }).click();
		await expect(page.getByTestId("flash-toast")).toBeVisible();

		// Navigate away client-side, then restore the page from history.
		await page.getByRole("link", { name: "← Home" }).click();
		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample", level: 1 }),
		).toBeVisible();
		await page.goBack();

		// The page object was restored from history state — where the client
		// deliberately stores flash as {} — so the toast must not reappear.
		await expect(
			page.getByRole("heading", { name: "Flash native", level: 1 }),
		).toBeVisible();
		await expect(page.getByTestId("flash-toast")).toHaveCount(0);
	});
});
