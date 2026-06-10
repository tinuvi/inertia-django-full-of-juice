import { expect, test } from "@playwright/test";

test.describe("Precognition — live form validation", () => {
	test("an invalid field validates over the wire and renders its error", async ({
		page,
	}) => {
		await page.goto("/precognition/");

		const validation = page.waitForResponse(
			(r) =>
				r.url().endsWith("/precognition/submit/") &&
				r.request().headers().precognition === "true",
		);
		await page.getByTestId("email-input").fill("not-an-email");
		await page.getByTestId("email-input").blur();
		const response = await validation;

		// Wire: Precognition + Validate-Only on the request; 422 with the
		// Precognition echo (the client throws without it) on the response.
		expect(response.request().headers()["precognition-validate-only"]).toBe(
			"email",
		);
		expect(response.status()).toBe(422);
		expect(response.headers().precognition).toBe("true");
		expect(response.headers().vary).toContain("Precognition");
		const body = await response.json();
		expect(body.message).toBe("The given data was invalid.");
		expect(Object.keys(body.errors)).toEqual(["email"]);

		await expect(page.getByTestId("email-error")).toBeVisible();
	});

	test("fixing the field yields a 204 success and the valid marker", async ({
		page,
	}) => {
		await page.goto("/precognition/");

		const validation = page.waitForResponse(
			(r) =>
				r.url().endsWith("/precognition/submit/") &&
				r.request().headers().precognition === "true",
		);
		await page.getByTestId("email-input").fill("ada@example.com");
		await page.getByTestId("email-input").blur();
		const response = await validation;

		expect(response.status()).toBe(204);
		expect(response.headers().precognition).toBe("true");
		expect(response.headers()["precognition-success"]).toBe("true");

		await expect(page.getByTestId("email-valid")).toBeVisible();
		await expect(page.getByTestId("email-error")).toHaveCount(0);
	});

	test("only the touched field is validated — others stay silent", async ({
		page,
	}) => {
		await page.goto("/precognition/");

		await page.getByTestId("age-input").fill("12");
		await page.getByTestId("age-input").blur();

		await expect(page.getByTestId("age-error")).toBeVisible();
		// name/email were never touched: the validate-only scoping popped
		// them off the form, so no required-field noise leaks in.
		await expect(page.getByTestId("name-error")).toHaveCount(0);
		await expect(page.getByTestId("email-error")).toHaveCount(0);
	});

	test("a real submit with valid data redirects past the decorator", async ({
		page,
	}) => {
		await page.goto("/precognition/");

		await page.getByTestId("name-input").fill("Ada");
		await page.getByTestId("email-input").fill("ada@example.com");
		await page.getByTestId("age-input").fill("30");
		await page.getByRole("button", { name: "Sign up" }).click();

		await expect(page).toHaveURL(/\/precognition\/\?signed=1$/);
	});

	test("a real submit with invalid data falls back to the errors flow", async ({
		page,
	}) => {
		await page.goto("/precognition/");

		await page.getByTestId("name-input").fill("Ada");
		await page.getByTestId("email-input").fill("nope");
		await page.getByTestId("age-input").fill("30");
		await page.getByRole("button", { name: "Sign up" }).click();

		await expect(page.getByTestId("email-error")).toBeVisible();
		await expect(page).toHaveURL(/\/precognition\/$/);
	});
});
