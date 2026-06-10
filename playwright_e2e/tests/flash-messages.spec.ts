import { expect, test } from "@playwright/test";

test.describe("Flash — Django messages as one-shot shared props", () => {
	test("POST → redirect surfaces messages on the followed GET", async ({
		page,
	}) => {
		await page.goto("/flash/");
		await expect(page.getByText("No flash messages.")).toBeVisible();

		// router.post → 302 → the browser follows with a GET; the middleware
		// drains contrib.messages into props.messages on that one. Playwright
		// only reports provisional request headers on browser-followed redirect
		// hops, so match the hop via redirectedFrom() and prove the server saw
		// X-Inertia via the response header instead.
		const followUp = page.waitForResponse((r) =>
			(r.request().redirectedFrom()?.url() ?? "").endsWith("/flash/notify/"),
		);
		await page.getByRole("button", { name: "Save profile" }).click();
		const response = await followUp;
		expect(response.headers()["x-inertia"]).toBe("true");
		const pageObject = await response.json();

		expect(pageObject.props.messages).toEqual([
			expect.objectContaining({
				message: "Profile saved successfully.",
				level_tag: "success",
			}),
			expect.objectContaining({
				message: "Subscription expires soon.",
				level_tag: "warning",
			}),
		]);
		// No `flash` page field — the messages ride as plain shared props.
		expect(pageObject).not.toHaveProperty("flash");

		await expect(
			page.getByText("[success] Profile saved successfully."),
		).toBeVisible();
		await expect(
			page.getByText("[warning] Subscription expires soon."),
		).toBeVisible();
	});

	test("messages are one-shot — gone after the next request", async ({
		page,
	}) => {
		await page.goto("/flash/");
		await page.getByRole("button", { name: "Save profile" }).click();
		await expect(
			page.getByText("[success] Profile saved successfully."),
		).toBeVisible();

		// get_messages consumed the storage when it shared them; a full reload
		// renders an empty list without any extra cleanup code.
		await page.reload();
		await expect(page.getByText("No flash messages.")).toBeVisible();
	});
});
