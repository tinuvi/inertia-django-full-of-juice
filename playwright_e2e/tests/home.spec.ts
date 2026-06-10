import { expect, test } from "@playwright/test";

test.describe("Home — page shell & shared props", () => {
	test("serves the v3 page shell, not the legacy data-page div", async ({
		request,
	}) => {
		const response = await request.get("/");
		expect(response.ok()).toBeTruthy();

		const html = await response.text();
		expect(html).toContain('<script data-page="app" type="application/json">');
		expect(html).toContain('<div id="app"></div>');
		expect(html).not.toMatch(/<div id="app" data-page=/);
	});

	test("page-shell JSON auto-injects errors:{} and omits unset conditional fields", async ({
		request,
	}) => {
		const html = await (await request.get("/")).text();
		const match = html.match(
			/<script data-page="app" type="application\/json">(.*?)<\/script>/s,
		);
		expect(match, "page-shell <script> not found").not.toBeNull();

		const page = JSON.parse((match as RegExpMatchArray)[1]);
		// errors is auto-injected even when the view never sets it.
		expect(page.props.errors).toEqual({});
		// v3 only-when-true: these are absent unless the view opts in.
		expect(page).not.toHaveProperty("encryptHistory");
		expect(page).not.toHaveProperty("clearHistory");
		expect(page).not.toHaveProperty("preserveFragment");
		// ❌-by-design page fields: never emitted, and client-tolerant — the
		// v3 client defaults each when absent (see the README feature matrix).
		expect(page).not.toHaveProperty("sharedProps");
		expect(page).not.toHaveProperty("rescuedProps");
		expect(page).not.toHaveProperty("flash");
		expect(page.component).toBe("Home");
	});

	test("boots the React app and renders shared props", async ({ page }) => {
		await page.goto("/");

		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample", level: 1 }),
		).toBeVisible();
		await expect(page.getByText("Welcome, Brandon (goalie).")).toBeVisible();
		await expect(page.getByText(/Library version:/)).toBeVisible();
	});

	test("client-side navigates to Lists without a full document reload", async ({
		page,
	}) => {
		await page.goto("/");

		await page.evaluate(() => {
			(window as unknown as { __noReload: boolean }).__noReload = true;
		});

		await page.getByRole("link", { name: /^Lists/ }).click();

		await expect(
			page.getByRole("heading", { name: "List props", level: 1 }),
		).toBeVisible();
		await expect(page).toHaveURL(/\/lists\/$/);

		const survivedReload = await page.evaluate(
			() =>
				(window as unknown as { __noReload?: boolean }).__noReload === true,
		);
		expect(survivedReload).toBe(true);
	});
});
