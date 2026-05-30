import { expect, test } from "@playwright/test";

test.describe("Redirects", () => {
	test("inertia_redirect() navigates the client to /lists/", async ({
		page,
	}) => {
		// Triggered as an Inertia visit (XHR) so the 409 + X-Inertia-Redirect is
		// honored by the client — a hard navigation to the endpoint would not be.
		await page.goto("/");

		await page.getByRole("link", { name: /inertia_redirect\(\)/ }).click();

		await expect(page).toHaveURL(/\/lists\/$/);
		await expect(
			page.getByRole("heading", { name: "List props", level: 1 }),
		).toBeVisible();
		await expect(page.locator("pre").first()).toContainText("Brandon");
	});

	test("middleware rewrites a #fragment 302 into a client redirect", async ({
		page,
	}) => {
		await page.goto("/");

		await page.getByRole("link", { name: /Fragment redirect/ }).click();

		// redirect("/lists/#users") (302) → InertiaMiddleware rewrites to a
		// 409 + X-Inertia-Redirect so the fragment survives.
		await expect(page).toHaveURL(/\/lists\/#users$/);
		await expect(
			page.getByRole("heading", { name: "List props", level: 1 }),
		).toBeVisible();
	});

	test("preserve_fragment() carries the #users fragment to the redirect target", async ({
		page,
	}) => {
		await page.goto("/");

		await page
			.getByRole("link", { name: /preserve_fragment\(\)/ })
			.click();

		await expect(page).toHaveURL(/\/lists\/#users$/);
		await expect(
			page.getByRole("heading", { name: "List props", level: 1 }),
		).toBeVisible();
	});

	test("location() triggers a hard navigation to the external URL", async ({
		page,
	}) => {
		// Stub example.com so the assertion stays hermetic (no real network).
		await page.route("https://example.com/**", (route) =>
			route.fulfill({
				contentType: "text/html",
				body: "<h1>stubbed external</h1>",
			}),
		);

		await page.goto("/");
		await page.getByRole("link", { name: /location\(\)/ }).click();

		// The view returns 409 + X-Inertia-Location: https://example.com/ and the
		// v3 client performs a full browser navigation to it.
		await page.waitForURL("https://example.com/**");
		expect(page.url()).toContain("example.com");
	});
});
