import { Link, router, usePage } from "@inertiajs/react";

type Props = {
	name: string;
	sport?: string;
	team?: string;
	grit?: string;
	plans?: string[];
	topic?: string;
};

export default function Lazy() {
	const { props } = usePage<Props>();

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Lazy props</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<pre>{JSON.stringify(props, null, 2)}</pre>
			<div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
				<button
					type="button"
					onClick={() => router.reload({ only: ["sport"] })}
				>
					Load `sport` (optional)
				</button>
				<button
					type="button"
					onClick={() => router.reload({ only: ["team", "grit"] })}
				>
					Load `team` + `grit` (deferred)
				</button>
				<button type="button" onClick={() => router.reload({ only: ["grit"] })}>
					Reload `extras` group only
				</button>
				<button
					type="button"
					onClick={() => router.reload({ reset: ["plans"] })}
				>
					Reset `plans` (once)
				</button>
				<button
					type="button"
					onClick={() => router.reload({ except: ["name"] })}
				>
					Reload except `name`
				</button>
				<button type="button" onClick={() => router.reload()}>
					Reload all
				</button>
			</div>
		</main>
	);
}
