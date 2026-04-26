const pages = import.meta.glob("./pages/*.tsx", { eager: true }) as Record<
	string,
	{ default: unknown }
>;

export const resolvePage = (name: string) => {
	const module = pages[`./pages/${name}.tsx`];
	if (!module) {
		throw new Error(`Page not found: ${name}`);
	}
	return module.default;
};
