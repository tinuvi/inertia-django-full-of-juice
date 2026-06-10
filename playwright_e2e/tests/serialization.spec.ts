import { expect, test } from "@playwright/test";

test.describe("Roster — Model / QuerySet serialization", () => {
	test("QuerySet props serialize via InertiaMeta.fields", async ({
		request,
	}) => {
		const html = await (await request.get("/roster/")).text();
		const match = html.match(
			/<script data-page="app" type="application\/json">(.*?)<\/script>/s,
		);
		expect(match, "page-shell <script> not found").not.toBeNull();

		const page = JSON.parse((match as RegExpMatchArray)[1]);
		// Exact match on purpose: proves InertiaMeta field filtering (no `id`,
		// no `scouting_notes`), DateTimeField → ISO-8601 string, and
		// DecimalField → string, straight from a QuerySet prop.
		expect(page.props.players).toEqual([
			{
				name: "Brian",
				position: "Center",
				number: 9,
				salary: "980.00",
				joined_at: "2026-03-02T18:00:00Z",
			},
			{
				name: "Brandon",
				position: "Goalie",
				number: 30,
				salary: "1250.50",
				joined_at: "2026-01-15T10:30:00Z",
			},
		]);
	});

	test("the model-backed rows render in the browser", async ({ page }) => {
		await page.goto("/roster/");

		await expect(page.getByRole("heading", { name: "Roster" })).toBeVisible();
		const rows = page.locator("tbody tr");
		await expect(rows).toHaveCount(2);
		await expect(rows.nth(0)).toContainText("Brian");
		await expect(rows.nth(1)).toContainText("Brandon");
		await expect(page.getByText("1250.50")).toBeVisible();
		await expect(page.getByText("TOP SECRET")).toHaveCount(0);
	});
});
