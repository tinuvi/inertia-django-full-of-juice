import { Link, router } from "@inertiajs/react";

export default function Method() {
	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Method conversion (303)</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<p>
				These buttons issue PUT / PATCH / DELETE. The InertiaMiddleware converts
				the server-side 302 redirect into a <strong>303</strong> so the v3
				client follows with a GET (per the v3 protocol).
			</p>
			<div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
				<button type="button" onClick={() => router.put("/method/submit/")}>
					PUT /method/submit/
				</button>
				<button type="button" onClick={() => router.patch("/method/submit/")}>
					PATCH /method/submit/
				</button>
				<button type="button" onClick={() => router.delete("/method/submit/")}>
					DELETE /method/submit/
				</button>
			</div>
		</main>
	);
}
