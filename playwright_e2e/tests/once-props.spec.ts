import { expect, test } from "@playwright/test";

test.describe("Lazy — once props", () => {
	test("page shell registers once props under their effective keys", async ({
		request,
	}) => {
		const html = await (await request.get("/lazy/")).text();
		const match = html.match(
			/<script data-page="app" type="application\/json">(.*?)<\/script>/s,
		);
		expect(match, "page-shell <script> not found").not.toBeNull();

		const page = JSON.parse((match as RegExpMatchArray)[1]);
		// Once props resolve on first load like regular props...
		expect(page.props.plans).toEqual(["A", "B"]);
		expect(page.props.topic).toBe("Hockey");
		// ...and the onceProps registry tells the client what to cache. The
		// entry key is the custom key= when given, the prop name otherwise.
		expect(page.onceProps["lazy-topic-v1"]).toEqual({
			prop: "topic",
			expiresAt: null,
		});
		expect(page.onceProps.plans.prop).toBe("plans");
		// expires_in=5min becomes an absolute unix-ms timestamp.
		expect(typeof page.onceProps.plans.expiresAt).toBe("number");
	});

	test("a reload skips cached once props but fresh=True re-resolves", async ({
		page,
	}) => {
		await page.goto("/lazy/");
		const pre = page.locator("pre");
		// Let the automatic deferred-group fetches settle first.
		await expect(pre).toContainText('"grit": "intense"');

		// The button's router.reload() is the only follow-up request without
		// X-Inertia-Partial-Data (the deferred fetches are group-scoped).
		const reload = page.waitForResponse((r) => {
			const headers = r.request().headers();
			return (
				r.url().endsWith("/lazy/") &&
				headers["x-inertia"] === "true" &&
				!headers["x-inertia-partial-data"]
			);
		});
		await page.getByRole("button", { name: "Reload all" }).click();
		const response = await reload;

		// The client advertises every once key it has cached.
		const exceptOnce =
			response.request().headers()["x-inertia-except-once-props"] ?? "";
		expect(exceptOnce.split(",").sort()).toEqual(["lazy-topic-v1", "plans"]);

		const pageObject = await response.json();
		// `plans` is cached and not fresh → the server skips recomputing it.
		expect(Object.keys(pageObject.props)).not.toContain("plans");
		// `topic` is fresh=True → it survives except-once and is re-sent.
		expect(pageObject.props.topic).toBe("Hockey");
		// The registry entry must still ride along even though the value is
		// omitted — without it the client would forget its cached value.
		expect(pageObject.onceProps.plans.prop).toBe("plans");

		// The client fills the gap from its cache — plans never leaves the UI.
		await expect(pre).toContainText('"plans"');
	});

	test("reset makes the server recompute and re-send a once prop", async ({
		page,
	}) => {
		await page.goto("/lazy/");
		const pre = page.locator("pre");
		await expect(pre).toContainText('"grit": "intense"');

		const reset = page.waitForResponse((r) => {
			const resetHeader = r.request().headers()["x-inertia-reset"] ?? "";
			return r.url().endsWith("/lazy/") && resetHeader.includes("plans");
		});
		await page.getByRole("button", { name: /Reset `plans`/ }).click();
		const response = await reset;

		// reset rides a partial reload scoped to the prop; the client still
		// advertises its cache, but in-partial-data wins over except-once.
		const requestHeaders = response.request().headers();
		expect(requestHeaders["x-inertia-partial-data"]).toBe("plans");
		expect(requestHeaders["x-inertia-except-once-props"]).toContain("plans");

		const pageObject = await response.json();
		expect(pageObject.props.plans).toEqual(["A", "B"]);
		// No onceProps registry on this response: `plans` is stripped by
		// X-Inertia-Reset and `topic` falls outside the partial data set.
		expect(pageObject.onceProps).toBeUndefined();
	});
});
