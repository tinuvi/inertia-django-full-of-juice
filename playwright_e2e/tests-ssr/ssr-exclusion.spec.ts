import { expect, test } from "@playwright/test";

/**
 * Runs against the `with-ssr` service (:8001): SSR enabled, with
 * INERTIA_SSR_EXCLUDE=^/lists/. So `/` is server-rendered, but `/lists/` is
 * excluded and falls back to the inline-JSON client shell.
 */
test.describe("SSR route exclusion (INERTIA_SSR_EXCLUDE)", () => {
	test("a non-excluded route is server-rendered", async ({ request }) => {
		const html = await (await request.get("/")).text();

		// The Inertia SSR renderer marks the mount node and injects the rendered
		// component into the body before any JS runs. (If the SSR sidecar were
		// down the library would fall back to the inline shell and this marker
		// would be absent — so this also proves SSR is genuinely engaged.)
		expect(html).toContain('data-server-rendered="true"');
		// The <h1> text is a single contiguous node in the server-rendered markup.
		expect(html).toContain("<h1>Inertia Django Sample</h1>");
	});

	test("an excluded route falls back to the inline-JSON client shell", async ({
		request,
	}) => {
		const html = await (await request.get("/lists/")).text();

		// /lists/ matches ^/lists/ → SSR is skipped. The shell is the inline
		// page-data <script> + an empty, un-rendered mount node.
		expect(html).toContain('<script data-page="app" type="application/json">');
		expect(html).toContain('<div id="app"></div>');
		expect(html).not.toContain('data-server-rendered="true"');
		expect(html).not.toContain("List props");
	});

	test("both routes still render in the browser after hydration", async ({
		page,
	}) => {
		await page.goto("/");
		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample" }),
		).toBeVisible();

		await page.goto("/lists/");
		await expect(
			page.getByRole("heading", { name: "List props" }),
		).toBeVisible();
	});
});
