import { Link, router, usePage } from "@inertiajs/react";

type Item = { id: number; title: string };

type Props = {
	items: Item[];
};

export default function Feed() {
	const { props } = usePage<Props>();
	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Feed (infinite_scroll)</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<ul>
				{props.items.map((item) => (
					<li key={item.id}>{item.title}</li>
				))}
			</ul>
			<div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
				<button
					type="button"
					onClick={() => router.reload({ only: ["items"], data: { page: 2 } })}
				>
					Load next page (append)
				</button>
				<button
					type="button"
					onClick={() =>
						router.reload({
							only: ["items"],
							data: { page: 1 },
							headers: {
								"X-Inertia-Infinite-Scroll-Merge-Intent": "prepend",
							},
						})
					}
				>
					Load older (prepend)
				</button>
				<button
					type="button"
					onClick={() => router.reload({ only: ["items"], reset: ["items"] })}
				>
					Reset feed
				</button>
			</div>
		</main>
	);
}
