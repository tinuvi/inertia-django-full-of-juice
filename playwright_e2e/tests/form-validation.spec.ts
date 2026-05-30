import { expect, test } from "@playwright/test";

test.describe("Form — useForm validation flow", () => {
	test("renders inline server errors on an empty submit", async ({ page }) => {
		await page.goto("/form/");

		await page.getByRole("button", { name: "Submit" }).click();

		// errors come back as an Inertia 200 with props.errors; the client keeps
		// us on the Form component and renders them inline.
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
});
