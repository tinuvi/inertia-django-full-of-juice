import { Link, router, usePage } from "@inertiajs/react";

type Props = {
	name: string;
	sport?: string;
	team?: string;
	grit?: string;
	plans?: string[];
};

export default function Lazy() {
	const { props } = usePage<Props>();

	const reload = (only: string[]) => router.reload({ only });

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Lazy props</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<pre>{JSON.stringify(props, null, 2)}</pre>
			<button type="button" onClick={() => reload(["sport"])}>
				Load `sport` (optional)
			</button>{" "}
			<button type="button" onClick={() => reload(["team", "grit"])}>
				Load `team` + `grit` (deferred)
			</button>{" "}
			<button type="button" onClick={() => router.reload()}>
				Reload all
			</button>
		</main>
	);
}
