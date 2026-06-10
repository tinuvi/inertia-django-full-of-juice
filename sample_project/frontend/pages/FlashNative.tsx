import { Link, router, usePage } from "@inertiajs/react";
import { useEffect, useState } from "react";

type Toast = { text: string; kind: string };

export default function FlashNative() {
	// `flash` is a first-class page-object field: replaced wholesale on each
	// response, stripped from history state by the client (no replay on
	// back/forward), and mirrored by the global `flash` event.
	const { flash } = usePage();
	const toast = flash.toast as Toast | undefined;
	const [eventLog, setEventLog] = useState<string[]>([]);

	useEffect(() => {
		return router.on("flash", (event) => {
			const flashed = event.detail.flash.toast as Toast | undefined;
			if (flashed) {
				setEventLog((log) => [...log, `event: ${flashed.text}`]);
			}
		});
	}, []);

	const save = () => {
		router.post("/flash-native/save/");
	};

	return (
		<main style={{ fontFamily: "system-ui", padding: 24 }}>
			<h1>Flash native</h1>
			<p>
				<Link href="/">← Home</Link>
			</p>
			<button type="button" onClick={save}>
				Save
			</button>
			{toast && (
				<div data-testid="flash-toast" data-kind={toast.kind}>
					{toast.text}
				</div>
			)}
			<ul data-testid="flash-event-log">
				{eventLog.map((entry) => (
					<li key={entry}>{entry}</li>
				))}
			</ul>
		</main>
	);
}
