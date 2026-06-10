import { expect, test } from "@playwright/test";

test.describe("Bags — error bags scope two forms on one page", () => {
	test("a failed submit nests errors under the visit's bag", async ({
		page,
	}) => {
		await page.goto("/bags/");

		const submit = page.waitForResponse(
			(r) =>
				r.url().endsWith("/bags/newsletter/") &&
				r.request().method() === "POST",
		);
		const followUp = page.waitForResponse(
			(r) =>
				new URL(r.url()).pathname === "/bags/" &&
				r.request().method() === "GET",
		);
		await page.getByRole("button", { name: "Subscribe" }).click();
		const response = await submit;

		// Wire: the POST carries the bag name and `back()` answers with a
		// redirect after flashing the errors to the session…
		expect(response.request().headers()["x-inertia-error-bag"]).toBe(
			"newsletter",
		);
		expect(response.status()).toBe(302);

		// …the browser re-sends the bag header while following the redirect,
		// and the built-in errors flow nests the flashed errors under it.
		// (allHeaders(): plain headers() only reports provisional headers on
		// redirect-followed requests and omits custom ones.)
		const followed = await followUp;
		expect((await followed.request().allHeaders())["x-inertia-error-bag"]).toBe(
			"newsletter",
		);
		const pageObject = await followed.json();
		expect(pageObject.props.errors).toEqual({
			newsletter: { email: "Email is invalid" },
		});

		// The client unwraps errors[bag] into the submitting form only.
		await expect(page.getByText("Email is invalid")).toBeVisible();
		await expect(page.locator('[data-bag="feedback"]')).toHaveCount(0);
	});

	test("each form keeps its own bag across sibling submits", async ({
		page,
	}) => {
		await page.goto("/bags/");

		await page.getByRole("button", { name: "Send feedback" }).click();
		await expect(page.getByText("Comment is required")).toBeVisible();
		await expect(page.locator('[data-bag="newsletter"]')).toHaveCount(0);

		// Failing the other form replaces props.errors wholesale, but each
		// useForm holds its own local error state — feedback's stays rendered.
		await page.getByRole("button", { name: "Subscribe" }).click();
		await expect(page.getByText("Email is invalid")).toBeVisible();
		await expect(page.getByText("Comment is required")).toBeVisible();
	});

	test("a valid submit follows the redirect", async ({ page }) => {
		await page.goto("/bags/");

		await page.getByLabel("Email").fill("brandon@example.com");
		await page.getByRole("button", { name: "Subscribe" }).click();

		await expect(page).toHaveURL(/\/bags\/\?subscribed=1$/);
	});
});
