import { Link, router, usePage } from "@inertiajs/react";

type Props = {
	users: { id: number; name: string }[];
	notifications: string[];
	filters: Record<string, unknown>;
};

export default function Lists() {
	const { props } = usePage<Props>();

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>List props</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<h2 id="users">users (merge + match_on=id)</h2>
			<pre>{JSON.stringify(props.users, null, 2)}</pre>
			<h2>notifications (prepend)</h2>
			<pre>{JSON.stringify(props.notifications, null, 2)}</pre>
			<h2>filters (deep_merge)</h2>
			<pre>{JSON.stringify(props.filters, null, 2)}</pre>
			<button type="button" onClick={() => router.reload({ only: ["users"] })}>
				Refresh users
			</button>
		</main>
	);
}
