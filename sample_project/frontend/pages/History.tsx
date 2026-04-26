import { Link, usePage } from "@inertiajs/react";

type Props = {
	note: string;
};

type Page = {
	encryptHistory?: boolean;
	clearHistory?: boolean;
};

export default function History() {
	const page = usePage<Props>();
	const { props } = page;
	const raw = page as unknown as Page;

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>History controls</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<p>{props.note}</p>
			<ul>
				<li>
					<code>encryptHistory</code>:{" "}
					{raw.encryptHistory ? "true" : "(absent)"}
				</li>
				<li>
					<code>clearHistory</code>: {raw.clearHistory ? "true" : "(absent)"}
				</li>
			</ul>
			<p>
				<a href="/clear-history/">Clear history (server-flash → redirect)</a>
			</p>
		</main>
	);
}
