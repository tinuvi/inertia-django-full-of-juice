import { expect, test } from "@playwright/test";

/**
 * Proves the v3.6 background-vs-sync behavior of an asset-version-change 409.
 *
 * InertiaMiddleware.force_refresh now echoes the CURRENT server version in
 * `X-Inertia-Version` on the stale-version 409. With @inertiajs/core >= 3.6.0
 * the client's `locationVisit` reads that header and, when the version
 * changed, suppresses the forced reload for *background* (async) visits —
 * `usePoll`, `router.reload()` — while a user-initiated (sync) visit still
 * hard-navigates. Without the header the client cannot tell the version
 * apart, so it would reload even background polls (the bug this guards).
 *
 * The `/poll/` page mounts `usePoll`; the test-only `/__e2e__/version/`
 * endpoint (gated behind E2E_TEST_HOOKS, on for the without-ssr E2E service)
 * flips the server's asset version at runtime.
 *
 * Serial + reset-in-afterEach: these tests mutate one piece of shared,
 * process-wide server state (the asset version). The suite runs single-worker
 * / not-fully-parallel, so resetting the override after each test keeps every
 * other spec seeing the default "1.0".
 */

const CHANGED_VERSION = "v2-changed";
const POLL_HEADING = "Poll (usePoll background reloads)";

type MarkerWindow = { __e2eMarker?: string };

// The next poll tick after a version flip: a background reload of /poll/ that
// the server answers with a version-change 409.
const isPoll409 = (res: { url: () => string; status: () => number }) =>
	new URL(res.url()).pathname === "/poll/" && res.status() === 409;

test.describe("Asset versioning — background 409 suppression (v3.6)", () => {
	test.describe.configure({ mode: "serial" });

	// Reset before and after so a crashed prior run cannot leak a stale
	// override into this spec, and this spec cannot leak one into the next.
	test.beforeEach(async ({ request }) => {
		await request.delete("/__e2e__/version/");
	});
	test.afterEach(async ({ request }) => {
		await request.delete("/__e2e__/version/");
	});

	test("a background usePoll 409 with a changed version is suppressed (no hard reload)", async ({
		page,
		request,
	}) => {
		await page.goto("/poll/");
		await expect(
			page.getByRole("heading", { name: POLL_HEADING }),
		).toBeVisible();
		const urlBefore = page.url();

		// In-flight state a hard reload would destroy: a window marker and a
		// typed-but-unsubmitted input value.
		await page.evaluate(() => {
			(window as unknown as MarkerWindow).__e2eMarker = "alive";
		});
		await page.getByTestId("in-flight").fill("draft text");

		// Flip the server's asset version out from under the running client.
		const flip = await request.post("/__e2e__/version/", {
			data: { version: CHANGED_VERSION },
		});
		expect(flip.ok()).toBeTruthy();
		expect(await flip.json()).toEqual({ version: CHANGED_VERSION });

		// The next background poll tick now mismatches → 409 carrying the new
		// version. Wait for that exact response instead of sleeping.
		await page.waitForResponse(isPoll409);

		// The fix: a background visit's version-change 409 is swallowed — no
		// reload — so all in-flight state survives and the URL is unchanged.
		expect(
			await page.evaluate(
				() => (window as unknown as MarkerWindow).__e2eMarker,
			),
		).toBe("alive");
		await expect(page.getByTestId("in-flight")).toHaveValue("draft text");
		expect(page.url()).toBe(urlBefore);
		// The client never adopted the new version (it did not reload).
		await expect(page.getByTestId("page-version")).toHaveText("1.0");

		// A second tick keeps getting 409s and stays suppressed — repeated
		// version-change polls do not accumulate into a reload.
		await page.waitForResponse(isPoll409);
		expect(
			await page.evaluate(
				() => (window as unknown as MarkerWindow).__e2eMarker,
			),
		).toBe("alive");
		await expect(page.getByTestId("in-flight")).toHaveValue("draft text");
		expect(page.url()).toBe(urlBefore);
	});

	test("a user-initiated visit still hard-navigates after a version change", async ({
		page,
		request,
	}) => {
		await page.goto("/poll/");
		await expect(
			page.getByRole("heading", { name: POLL_HEADING }),
		).toBeVisible();

		await page.evaluate(() => {
			(window as unknown as MarkerWindow).__e2eMarker = "alive";
		});

		await request.post("/__e2e__/version/", {
			data: { version: CHANGED_VERSION },
		});

		// Confirm staleness is live: the background poll 409s and is suppressed,
		// so the marker still survives right up until the user acts.
		await page.waitForResponse(isPoll409);
		expect(
			await page.evaluate(
				() => (window as unknown as MarkerWindow).__e2eMarker,
			),
		).toBe("alive");

		// A user-initiated (sync) visit — clicking a nav link — is NOT
		// suppressed: the same version-change 409 hard-navigates the browser.
		await page.getByRole("link", { name: /Home/ }).click();

		// waitForFunction survives the full-document navigation; the in-memory
		// marker is gone once the new document boots.
		await page.waitForFunction(
			() =>
				(window as unknown as MarkerWindow).__e2eMarker === undefined,
		);
		expect(new URL(page.url()).pathname).toBe("/");
		await expect(
			page.getByRole("heading", { name: "Inertia Django Sample", level: 1 }),
		).toBeVisible();

		// Recovery: the hard reload rebooted the client on the new version, so a
		// fresh visit back to /poll/ is served 200 (no more 409) and the page
		// now reports the changed version.
		const [pollResponse] = await Promise.all([
			page.waitForResponse((res) => new URL(res.url()).pathname === "/poll/"),
			page.getByRole("link", { name: /Poll/ }).click(),
		]);
		expect(pollResponse.status()).toBe(200);
		await expect(page.getByTestId("page-version")).toHaveText(CHANGED_VERSION);
	});
});
