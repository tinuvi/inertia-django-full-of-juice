import { Link, router, usePage } from "@inertiajs/react";

type FlashMessage = {
	message: string;
	level: number;
	tags: string;
	extra_tags: string | null;
	level_tag: string;
};

type Props = {
	messages?: FlashMessage[];
};

export default function Flash() {
	const { props } = usePage<Props>();
	const messages = props.messages ?? [];

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Flash messages</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<button type="button" onClick={() => router.post("/flash/notify/")}>
				Save profile
			</button>
			{messages.length === 0 ? (
				<p>No flash messages.</p>
			) : (
				<ul>
					{messages.map((m) => (
						<li key={`${m.level_tag}-${m.message}`} data-level={m.level_tag}>
							[{m.level_tag}] {m.message}
						</li>
					))}
				</ul>
			)}
		</main>
	);
}
