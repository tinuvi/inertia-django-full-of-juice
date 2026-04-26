import { Link } from "@inertiajs/react";
import { type FormEvent, useState } from "react";

type ApiErrors = { message: string; errors: Record<string, string> };

function getCsrfToken(): string {
	const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
	return match ? decodeURIComponent(match[1]) : "";
}

export default function Validate() {
	const [name, setName] = useState("");
	const [errors, setErrors] = useState<Record<string, string>>({});
	const [message, setMessage] = useState<string>("");

	const submit = async (event: FormEvent) => {
		event.preventDefault();
		setErrors({});
		setMessage("");

		const res = await fetch("/api/validate/", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": getCsrfToken(),
			},
			body: JSON.stringify({ name }),
			credentials: "same-origin",
		});

		if (res.status === 422) {
			const data = (await res.json()) as ApiErrors;
			setErrors(data.errors);
			setMessage(data.message);
			return;
		}
		setMessage(res.ok ? "OK (200)" : `HTTP ${res.status}`);
	};

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Validate (errors_response / useHttp pattern)</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<p>
				This page submits via plain <code>fetch</code> (not Inertia's{" "}
				<code>useForm</code>). The server returns <code>422 JSON</code> with
				<code> &#123;message, errors&#125;</code> on validation failure — the
				shape <code>useHttp</code> consumers expect.
			</p>
			<form
				onSubmit={submit}
				style={{ display: "grid", gap: 8, maxWidth: 320 }}
			>
				<label>
					Name
					<input
						value={name}
						onChange={(event) => setName(event.target.value)}
					/>
					{errors.name && <small style={{ color: "red" }}>{errors.name}</small>}
				</label>
				<button type="submit">Submit (plain XHR)</button>
				{message && <p>{message}</p>}
			</form>
		</main>
	);
}
