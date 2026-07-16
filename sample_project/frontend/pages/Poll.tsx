import { Link, usePage, usePoll } from "@inertiajs/react";
import { useState } from "react";

export default function Poll() {
	const page = usePage();
	// usePoll issues a background (async) router.reload() every 600ms. When the
	// server's asset version is flipped mid-session, that poll gets a
	// version-change 409 which the v3.6 client suppresses — no hard reload —
	// whereas a user-initiated visit (the "← Home" link) still hard-navigates.
	usePoll(600);
	// Captured once per document load. A hard reload boots a fresh document and
	// resets this, so a suppressed poll (value unchanged) is distinguishable
	// from a reload (value changes) even without the spec's window marker.
	const [mountedAt] = useState(() => Date.now());

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Poll (usePoll background reloads)</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<p>
				Asset version: <code data-testid="page-version">{page.version}</code>
			</p>
			<p>
				Mounted at: <code data-testid="mounted-at">{mountedAt}</code>
			</p>
			<p>
				<label>
					In-flight text (a hard reload would clear this):{" "}
					<input type="text" data-testid="in-flight" defaultValue="" />
				</label>
			</p>
		</main>
	);
}
