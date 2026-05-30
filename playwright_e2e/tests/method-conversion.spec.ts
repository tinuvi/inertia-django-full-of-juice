import { expect, test } from "@playwright/test";

const VERBS = [
	{ verb: "put", label: "PUT /method/submit/" },
	{ verb: "patch", label: "PATCH /method/submit/" },
	{ verb: "delete", label: "DELETE /method/submit/" },
];

test.describe("Method conversion (303)", () => {
	for (const { verb, label } of VERBS) {
		test(`${verb.toUpperCase()} redirect is converted to 303 and lands on Home`, async ({
			page,
		}) => {
			await page.goto("/method/");

			// Playwright observes the redirect response itself, before the client
			// follows it — the middleware must have turned the 302 into a 303.
			const submitResponse = page.waitForResponse((r) =>
				r.url().endsWith("/method/submit/"),
			);
			await page.getByRole("button", { name: label }).click();
			expect((await submitResponse).status()).toBe(303);

			await expect(page).toHaveURL(new RegExp(`/\\?method=${verb}$`));
			await expect(
				page.getByRole("heading", { name: "Inertia Django Sample", level: 1 }),
			).toBeVisible();
		});
	}
});
