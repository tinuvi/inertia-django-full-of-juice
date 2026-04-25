import { Link, router, usePage } from "@inertiajs/react";

type Props = {
	items: { id: number; title: string }[];
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
			<button type="button" onClick={() => router.reload({ only: ["items"] })}>
				Load next page
			</button>
		</main>
	);
}
