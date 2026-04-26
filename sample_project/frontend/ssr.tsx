import process from "node:process";
import { createInertiaApp } from "@inertiajs/react";
import createServer from "@inertiajs/react/server";
import ReactDOMServer from "react-dom/server";
import { resolvePage } from "@/inertia-resolver";

const port = Number.parseInt(process.env.NODE_PORT ?? "13714", 10);

createServer(
	(page) =>
		createInertiaApp({
			page,
			render: ReactDOMServer.renderToString,
			resolve: resolvePage,
			setup: ({ App, props }) => <App {...props} />,
		}),
	port,
);
