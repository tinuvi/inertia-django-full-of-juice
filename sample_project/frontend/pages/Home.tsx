import { Link, usePage } from "@inertiajs/react";

type SharedProps = {
	app_name: string;
	user: { name: string; role: string };
	version: string;
	errors: Record<string, string>;
};

export default function Home() {
	const { props } = usePage<SharedProps>();
	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>{props.app_name}</h1>
			<p>
				Welcome, {props.user.name} ({props.user.role}). Library version:{" "}
				{props.version}.
			</p>
			<ul>
				<li>
					<Link href="/lazy/">
						Lazy props (optional / defer / once / partial-data / partial-except
						/ reset)
					</Link>
				</li>
				<li>
					<Link href="/lists/">
						Lists (merge / prepend / deep_merge / match_on / defer+merge)
					</Link>
				</li>
				<li>
					<Link href="/feed/">
						Feed (infinite_scroll: append / prepend / reset)
					</Link>
				</li>
				<li>
					<Link href="/form/">Form (useForm + auto-injected errors)</Link>
				</li>
				<li>
					<Link href="/bags/">
						Bags (error bags: X-Inertia-Error-Bag scoping two forms)
					</Link>
				</li>
				<li>
					<Link href="/flash/">
						Flash (Django messages shared as one-shot props)
					</Link>
				</li>
				<li>
					<Link href="/roster/">
						Roster (Model / QuerySet serialization via InertiaMeta)
					</Link>
				</li>
				<li>
					<Link href="/validate/">
						Validate (errors_response + plain XHR / useHttp pattern)
					</Link>
				</li>
				<li>
					<Link href="/history/">
						History (encrypt_history / clear_history)
					</Link>
				</li>
				<li>
					<Link href="/method/">
						Method (303 conversion on PUT/PATCH/DELETE)
					</Link>
				</li>
				<li>
					<Link href="/inertia-redirect/">
						inertia_redirect() — 409 + X-Inertia-Redirect
					</Link>
				</li>
				<li>
					<Link href="/location/">
						location() — 409 + X-Inertia-Location (external)
					</Link>
				</li>
				<li>
					<Link href="/redirect-fragment/">
						Fragment redirect (middleware rewrites 302#frag → 409)
					</Link>
				</li>
				<li>
					<Link href="/preserve-fragment/#users">
						preserve_fragment() (carries `#users` through the redirect)
					</Link>
				</li>
			</ul>
		</main>
	);
}
