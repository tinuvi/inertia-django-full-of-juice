import { Link, router, usePage } from "@inertiajs/react";

type User = { id: number; name: string };
type Notification = { id: number; text: string };
type Bucket = { id: string; label: string; count: number };
type Order = { id: number; total: string };

type Props = {
	users: User[];
	notifications: Notification[];
	filters: { buckets: Bucket[] };
	recent_orders?: Order[];
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

			<h2>notifications (prepend + match_on=id)</h2>
			<pre>{JSON.stringify(props.notifications, null, 2)}</pre>

			<h2>filters (deep_merge + match_on=buckets.id)</h2>
			<pre>{JSON.stringify(props.filters, null, 2)}</pre>

			<h2>recent_orders (defer + merge=True + match_on=id)</h2>
			<pre>
				{JSON.stringify(
					props.recent_orders ?? "(deferred — click below)",
					null,
					2,
				)}
			</pre>

			<div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
				<button
					type="button"
					onClick={() => router.reload({ only: ["users"] })}
				>
					Refresh users
				</button>
				<button
					type="button"
					onClick={() => router.reload({ only: ["users"], reset: ["users"] })}
				>
					Reset users
				</button>
				<button
					type="button"
					onClick={() => router.reload({ only: ["recent_orders"] })}
				>
					Load `recent_orders` (deferred + merge)
				</button>
			</div>
		</main>
	);
}
