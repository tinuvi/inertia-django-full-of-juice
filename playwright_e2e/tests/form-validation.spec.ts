import { expect, test } from "@playwright/test";

test.describe("Form — useForm validation flow", () => {
	test("renders inline server errors on an empty submit", async ({ page }) => {
		await page.goto("/form/");

		await page.getByRole("button", { name: "Submit" }).click();

		// `redirect_back(request, errors=…)` redirects to the referring page; the client
		// follows and the next render pulls the flashed errors into
		// props.errors, rendering them inline on the same component.
		await expect(page.getByText("Name is required")).toBeVisible();
		await expect(page.getByText("Email is invalid")).toBeVisible();
		await expect(
			page.getByRole("heading", { name: "Form", level: 1 }),
		).toBeVisible();
	});

	test("submits valid data and follows the redirect to Home", async ({
		page,
	}) => {
		await page.goto("/form/");

		await page.getByLabel("Name").fill("Ada");
		await page.getByLabel("Email").fill("ada@example.com");
		await page.getByRole("button", { name: "Submit" }).click();

		await expect(page).toHaveURL(/\/\?submitted=1$/);
		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample", level: 1 }),
		).toBeVisible();
	});

	test("POSTs carry Django's CSRF cookie back as the X-CSRFToken header", async ({
		page,
	}) => {
		await page.goto("/form/");

		// InertiaMiddleware calls get_token() on every response, so the cookie
		// is set even though no Django template ever rendered a csrf tag.
		const cookies = await page.context().cookies();
		const csrf = cookies.find((cookie) => cookie.name === "csrftoken");
		expect(csrf?.value, "csrftoken cookie not set").toBeTruthy();

		const submit = page.waitForRequest(
			(req) =>
				req.method() === "POST" &&
				new URL(req.url()).pathname === "/form/submit/",
		);
		await page.getByRole("button", { name: "Submit" }).click();

		// The sample aligns the v3 client to Django's names via the `http`
		// option (csrftoken / X-CSRFToken) — see frontend/main.tsx. Without
		// this alignment Django would reject the POST with a 403.
		expect((await submit).headers()["x-csrftoken"]).toBe(csrf?.value);
	});
});
