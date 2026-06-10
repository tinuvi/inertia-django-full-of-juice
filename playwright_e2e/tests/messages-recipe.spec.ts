import { expect, test } from "@playwright/test";

/**
 * Pins the real-world behavior of the Django-messages recipe — the pattern a
 * production consumer runs: an eager middleware (ShareDemoMiddleware, the
 * onsen `DataShareMiddleware` shape) draining contrib.messages into a
 * `messages` shared prop on EVERY request — against the v3 `flash` page
 * field on identical flows. The recipe's sharp edges are pinned on purpose:
 * they document where the recipe is safe (single-hop PRG, see
 * flash-messages.spec.ts) and why the flash field exists. The chain routes
 * replicate the consumer's account-linking shape: queue → redirect into a
 * gate → the gate redirects again without rendering.
 */

const plant = (path: string) =>
	`fetch("${path}", { method: "POST", headers: { "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "" } }).then((r) => r.status)`;

test.describe("Messages recipe vs the flash field — consumer flows", () => {
	test("multi-hop redirect chain: the recipe loses the message at the gate", async ({
		page,
	}) => {
		// link-messages queues "Contas vinculadas com sucesso!" then 302s into
		// the gate, which 302s again without rendering. The eager middleware
		// drains the message on the gate request; its response never renders a
		// page — consumed, never delivered.
		await page.goto("/chain/link-messages/");

		await expect(page).toHaveURL(/\/chain\/final\/$/);
		await expect(page.getByTestId("no-recipe-messages")).toBeVisible();
		await expect(page.getByTestId("flash-toast")).toHaveCount(0);
	});

	test("multi-hop redirect chain: the flash field survives the same hops", async ({
		page,
	}) => {
		// Identical chain shape, but flash() is pull-at-render: the gate hop
		// renders nothing, so it cannot consume the flash.
		await page.goto("/chain/link-flash/");

		await expect(page).toHaveURL(/\/chain\/final\/$/);
		await expect(page.getByTestId("flash-toast")).toHaveText(
			"Contas vinculadas com sucesso!",
		);
		await expect(page.getByTestId("no-recipe-messages")).toBeVisible();
	});

	test("partial reload steals a pending recipe message — consumed, never delivered", async ({
		page,
	}) => {
		await page.goto("/chain/final/");

		// A JSON endpoint queues a message without rendering (the axios
		// pattern) — the message now sits pending in the messages cookie.
		const planted = await page.evaluate(plant("/chain/plant-message/"));
		expect(planted).toBe(200);

		// A partial reload drains the storage (eager middleware), but the
		// partial filter drops the `messages` prop — it isn't in `only`.
		const partial = page.waitForResponse(
			(r) =>
				new URL(r.url()).pathname === "/chain/final/" &&
				r.request().headers()["x-inertia-partial-data"] === "stamp",
		);
		await page.getByRole("button", { name: "Reload stamp" }).click();
		const pageObject = await (await partial).json();
		expect(pageObject.props).not.toHaveProperty("messages");

		await expect(page.getByTestId("no-recipe-messages")).toBeVisible();

		// The storage was cleared by the partial request: a full reload
		// proves the message is gone without ever reaching the screen.
		await page.reload();
		await expect(page.getByTestId("no-recipe-messages")).toBeVisible();
	});

	test("the same pending state via flash() is delivered by the partial reload", async ({
		page,
	}) => {
		await page.goto("/chain/final/");

		const planted = await page.evaluate(plant("/chain/plant-flash/"));
		expect(planted).toBe(200);

		// flash is a page-object field, not a prop: partial filtering never
		// touches it, so the very same partial reload delivers it.
		const partial = page.waitForResponse(
			(r) =>
				new URL(r.url()).pathname === "/chain/final/" &&
				r.request().headers()["x-inertia-partial-data"] === "stamp",
		);
		await page.getByRole("button", { name: "Reload stamp" }).click();
		const pageObject = await (await partial).json();
		expect(pageObject.flash).toEqual({
			toast: { text: "Pending toast", kind: "success" },
		});

		await expect(page.getByTestId("flash-toast")).toHaveText("Pending toast");
	});

	test("a 409 stale-version refresh does not consume pending recipe messages", async ({
		page,
	}) => {
		// The consumer's load-bearing middleware behavior: force_refresh
		// resets storage.used so the discarded stale render cannot eat the
		// pending message (mirrored for flash/errors by the 0.5.0 reflash).
		await page.goto("/chain/final/");
		const planted = await page.evaluate(plant("/chain/plant-message/"));
		expect(planted).toBe(200);

		const staleStatus = await page.evaluate(() =>
			fetch("/chain/final/", {
				headers: { "X-Inertia": "true", "X-Inertia-Version": "stale" },
			}).then((r) => r.status),
		);
		expect(staleStatus).toBe(409);

		// The follow-up real visit still delivers the message.
		await page.goto("/chain/final/");
		await expect(page.getByText("[success] Pending toast")).toBeVisible();
	});

	test("history restore replays recipe messages — and never the flash field", async ({
		page,
	}) => {
		// The recipe's messages are ordinary props, so they are baked into
		// the history state and replay on Back. The flash field is stripped
		// from history by the client (see flash.spec.ts for that half).
		await page.goto("/flash/");
		await page.getByRole("button", { name: "Save profile" }).click();
		await expect(
			page.getByText("[success] Profile saved successfully."),
		).toBeVisible();

		await page.getByRole("link", { name: "← Home" }).click();
		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample", level: 1 }),
		).toBeVisible();
		await page.goBack();

		// Pinned limitation: the already-consumed message renders again from
		// the restored props.
		await expect(
			page.getByText("[success] Profile saved successfully."),
		).toBeVisible();
	});
});
