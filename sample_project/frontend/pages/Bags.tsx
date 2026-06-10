import { Link, useForm } from "@inertiajs/react";

export default function Bags() {
	const newsletter = useForm({ email: "" });
	const feedback = useForm({ comment: "" });

	const subscribe = (event: React.FormEvent) => {
		event.preventDefault();
		// errorBag is a per-visit option: the client sends X-Inertia-Error-Bag
		// and unwraps props.errors[errorBag] into this form only.
		newsletter.post("/bags/newsletter/", { errorBag: "newsletter" });
	};

	const sendFeedback = (event: React.FormEvent) => {
		event.preventDefault();
		feedback.post("/bags/feedback/", { errorBag: "feedback" });
	};

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Error bags</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<form
				onSubmit={subscribe}
				style={{ display: "grid", gap: 8, maxWidth: 320 }}
			>
				<h2>Newsletter</h2>
				<label>
					Email
					<input
						value={newsletter.data.email}
						onChange={(event) =>
							newsletter.setData("email", event.target.value)
						}
					/>
					{newsletter.errors.email && (
						<small data-bag="newsletter" style={{ color: "red" }}>
							{newsletter.errors.email}
						</small>
					)}
				</label>
				<button type="submit" disabled={newsletter.processing}>
					Subscribe
				</button>
			</form>
			<form
				onSubmit={sendFeedback}
				style={{ display: "grid", gap: 8, maxWidth: 320 }}
			>
				<h2>Feedback</h2>
				<label>
					Comment
					<input
						value={feedback.data.comment}
						onChange={(event) =>
							feedback.setData("comment", event.target.value)
						}
					/>
					{feedback.errors.comment && (
						<small data-bag="feedback" style={{ color: "red" }}>
							{feedback.errors.comment}
						</small>
					)}
				</label>
				<button type="submit" disabled={feedback.processing}>
					Send feedback
				</button>
			</form>
		</main>
	);
}
