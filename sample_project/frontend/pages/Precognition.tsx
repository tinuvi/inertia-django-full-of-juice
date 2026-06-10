import { Link, useForm } from "@inertiajs/react";

export default function Precognition() {
	// useForm(method, url, data) binds the form for Precognition: validate()
	// fires a `Precognition: true` request scoped to the touched fields.
	const form = useForm("post", "/precognition/submit/", {
		name: "",
		email: "",
		age: "",
	});

	const submit = (event: React.FormEvent) => {
		event.preventDefault();
		form.submit();
	};

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Precognition</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			{form.validating && <p data-testid="validating">Validating…</p>}
			<form
				onSubmit={submit}
				style={{ display: "grid", gap: 8, maxWidth: 320 }}
			>
				<label>
					Name
					<input
						data-testid="name-input"
						value={form.data.name}
						onChange={(event) => form.setData("name", event.target.value)}
						onBlur={() => form.validate("name")}
					/>
					{form.invalid("name") && (
						<small data-testid="name-error" style={{ color: "red" }}>
							{form.errors.name}
						</small>
					)}
					{form.valid("name") && (
						<small data-testid="name-valid" style={{ color: "green" }}>
							Looks good
						</small>
					)}
				</label>
				<label>
					Email
					<input
						data-testid="email-input"
						value={form.data.email}
						onChange={(event) => form.setData("email", event.target.value)}
						onBlur={() => form.validate("email")}
					/>
					{form.invalid("email") && (
						<small data-testid="email-error" style={{ color: "red" }}>
							{form.errors.email}
						</small>
					)}
					{form.valid("email") && (
						<small data-testid="email-valid" style={{ color: "green" }}>
							Looks good
						</small>
					)}
				</label>
				<label>
					Age
					<input
						data-testid="age-input"
						value={form.data.age}
						onChange={(event) => form.setData("age", event.target.value)}
						onBlur={() => form.validate("age")}
					/>
					{form.invalid("age") && (
						<small data-testid="age-error" style={{ color: "red" }}>
							{form.errors.age}
						</small>
					)}
				</label>
				<button type="submit" disabled={form.processing}>
					Sign up
				</button>
			</form>
		</main>
	);
}
