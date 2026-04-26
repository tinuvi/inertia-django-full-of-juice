import { Link, useForm } from "@inertiajs/react";

export default function Form() {
	const form = useForm({ name: "", email: "" });

	const submit = (event: React.FormEvent) => {
		event.preventDefault();
		form.post("/form/submit/");
	};

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Form</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<form
				onSubmit={submit}
				style={{ display: "grid", gap: 8, maxWidth: 320 }}
			>
				<label>
					Name
					<input
						value={form.data.name}
						onChange={(event) => form.setData("name", event.target.value)}
					/>
					{form.errors.name && (
						<small style={{ color: "red" }}>{form.errors.name}</small>
					)}
				</label>
				<label>
					Email
					<input
						value={form.data.email}
						onChange={(event) => form.setData("email", event.target.value)}
					/>
					{form.errors.email && (
						<small style={{ color: "red" }}>{form.errors.email}</small>
					)}
				</label>
				<button type="submit" disabled={form.processing}>
					Submit
				</button>
			</form>
		</main>
	);
}
