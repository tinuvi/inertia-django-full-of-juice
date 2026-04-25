import { Link, usePage } from "@inertiajs/react";

type SharedProps = {
	app_name: string;
	user: { name: string; role: string };
	version: string;
	errors: Record<string, string>;
};

export default function Home() {
	const { props } = usePage<SharedProps>();
	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>{props.app_name}</h1>
			<p>
				Welcome, {props.user.name} ({props.user.role}). Library version:{" "}
				{props.version}.
			</p>
			<ul>
				<li>
					<Link href="/lazy/">Lazy props (optional / defer / once)</Link>
				</li>
				<li>
					<Link href="/lists/">
						Lists (merge / prepend / deep_merge / match_on)
					</Link>
				</li>
				<li>
					<Link href="/feed/">Feed (infinite_scroll)</Link>
				</li>
				<li>
					<Link href="/form/">Form (errors_response / inertia_redirect)</Link>
				</li>
				<li>
					<a href="/redirect-fragment/">
						Fragment redirect (preserve_fragment)
					</a>
				</li>
			</ul>
		</main>
	);
}
