import { Link, router, usePage } from "@inertiajs/react";

type RecipeMessage = {
	message: string;
	level_tag: string;
};

type Toast = { text: string; kind: string };

type Props = {
	stamp?: string;
	messages?: RecipeMessage[];
};

const csrfToken = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "";

const plant = (url: string) =>
	fetch(url, { method: "POST", headers: { "X-CSRFToken": csrfToken() } });

export default function Chain() {
	// Both one-shot channels on one page: the Django-messages recipe
	// (eager middleware → `messages` shared prop) and the v3 flash field.
	const page = usePage<Props>();
	const messages = page.props.messages ?? [];
	const toast = page.flash.toast as Toast | undefined;

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Chain terminus</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<p data-testid="stamp">stamp: {page.props.stamp}</p>
			<p>
				<button type="button" onClick={() => plant("/chain/plant-message/")}>
					Plant message
				</button>
				<button type="button" onClick={() => plant("/chain/plant-flash/")}>
					Plant flash
				</button>
				<button
					type="button"
					onClick={() => router.reload({ only: ["stamp"] })}
				>
					Reload stamp
				</button>
			</p>
			{toast && (
				<div data-testid="flash-toast" data-kind={toast.kind}>
					{toast.text}
				</div>
			)}
			{messages.length === 0 ? (
				<p data-testid="no-recipe-messages">No recipe messages.</p>
			) : (
				<ul data-testid="recipe-messages">
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
