import { expect, test } from "@playwright/test";

test.describe("Rescue — defer(rescue=True) + rescuedProps", () => {
	test("a throwing rescuable resolver yields rescuedProps, not a 500", async ({
		page,
	}) => {
		const statsFetch = page.waitForResponse(
			(r) =>
				new URL(r.url()).pathname === "/rescue/" &&
				r.request().headers()["x-inertia-partial-data"] === "stats",
		);
		await page.goto("/rescue/");

		// Wire: the deferred fetch for the failing group comes back 200 with
		// the prop dropped from props and its key in rescuedProps.
		const response = await statsFetch;
		expect(response.status()).toBe(200);
		const pageObject = await response.json();
		expect(pageObject.rescuedProps).toEqual(["stats"]);
		expect(pageObject.props).not.toHaveProperty("stats");

		// The healthy sibling group still resolves…
		await expect(page.getByTestId("profile")).toHaveText("Profile: Brandon");
		// …and the <Deferred> rescue slot renders instead of the content.
		await expect(page.getByTestId("stats-rescue")).toBeVisible();
		await expect(page.getByTestId("stats")).toHaveCount(0);
	});

	test("the rescue slot's retry reload keeps the page alive", async ({
		page,
	}) => {
		await page.goto("/rescue/");
		await expect(page.getByTestId("stats-rescue")).toBeVisible();

		const retryFetch = page.waitForResponse(
			(r) =>
				new URL(r.url()).pathname === "/rescue/" &&
				r.request().headers()["x-inertia-partial-data"] === "stats",
		);
		await page.getByRole("button", { name: "Retry" }).click();
		await retryFetch;

		// The resolver still fails, so the rescue slot persists — the point
		// is the page survives repeated failures without crashing.
		await expect(page.getByTestId("stats-rescue")).toBeVisible();
		await expect(
			page.getByRole("heading", { name: "Rescue", level: 1 }),
		).toBeVisible();
	});
});
