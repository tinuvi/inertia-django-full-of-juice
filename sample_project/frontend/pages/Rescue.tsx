import { Deferred, Link, router } from "@inertiajs/react";

type Profile = { name: string };

export default function Rescue({
	profile,
	stats,
}: {
	profile?: Profile;
	stats?: Record<string, unknown>;
}) {
	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Rescue</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<Deferred data="profile" fallback={<p>Loading profile…</p>}>
				<p data-testid="profile">Profile: {profile?.name}</p>
			</Deferred>
			<Deferred
				data="stats"
				fallback={<p data-testid="stats-loading">Loading stats…</p>}
				rescue={({ reloading }) => (
					<div data-testid="stats-rescue">
						<p>Stats are unavailable right now.</p>
						<button
							type="button"
							disabled={reloading}
							onClick={() => router.reload({ only: ["stats"] })}
						>
							{reloading ? "Retrying…" : "Retry"}
						</button>
					</div>
				)}
			>
				<p data-testid="stats">{JSON.stringify(stats)}</p>
			</Deferred>
		</main>
	);
}
