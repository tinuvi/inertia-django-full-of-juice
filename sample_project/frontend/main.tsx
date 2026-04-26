import "vite/modulepreload-polyfill";
import { createInertiaApp } from "@inertiajs/react";
import { createRoot } from "react-dom/client";
import { resolvePage } from "@/inertia-resolver";

createInertiaApp({
	http: {
		xsrfCookieName: "csrftoken",
		xsrfHeaderName: "X-CSRFToken",
	},
	resolve: resolvePage,
	setup({ el, App, props }) {
		createRoot(el).render(<App {...props} />);
	},
});
