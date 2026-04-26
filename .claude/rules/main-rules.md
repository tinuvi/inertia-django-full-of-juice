# SDLC rules

Imperative guidance for working on `inertia-django-full-of-juice`. Follow these end-to-end on every change.

## Code style

- Write a test for every implementation change. No exception for "trivial" fixes.
- Use parameterized logging only: `logger.info("Message %s", value)`. Do **not** pre-format log strings with f-strings, `%`, or `.format()`.
- When you see `getLogger(__name__)`, change it to `getLogger("inertia_django_full_of_juice")`.
- Keep new code typed. The package ships PEP 561 typing — type-hint anything you add or touch.

## Testing

- Run the full library suite before declaring a change complete:
    ```bash
    docker compose run --remove-orphans --rm integration-tests
    ```
- When you change the v3 protocol surface (headers, page-object fields, middleware behavior, prop kinds), also walk `sample_project/E2E_TESTING.md` end-to-end against a live Django + Vite. Update the checklist in the same commit if the observable behavior changes.
- When the v3 protocol introduces new behavior, mirror Laravel's reference implementation (`inertiajs/inertia-laravel`, branch `3.x`). Cite the relevant Laravel file/line in the commit body when intentionally diverging.

## Lint & format

- Run after the implementation is complete (no need to re-run tests after):
    ```bash
    docker compose run --remove-orphans --rm lint-formatter
    ```
- For sample-project frontend changes, run from `sample_project/`:
    ```bash
    npm run format && npm run lint
    ```

## Documentation

- Update `CHANGELOG.md` under the active `[X.Y.Z]` heading on every user-visible change. Use `Added` / `Changed` / `Fixed` / `Removed` subsections.
- Update `sample_project/E2E_TESTING.md` whenever you add or change a v3 surface — add a row under the relevant section, not a one-off page.
- Update `README.md` when public API, install steps, or supported Python/Django versions change.
- Do **not** create new top-level docs (`*.md`) unless explicitly asked.

## Commits

- Use Conventional Commits.
- Split work so that one commit changes one concern. A library fix and a sample-project tweak go in two separate commits, even when discovered together.

## Deployment

- Releases are tag-driven via `.github/workflows/publish-package.yml`. Pushing an annotated tag matching the version number publishes to PyPI.
- Never edit `pyproject.toml`'s `version` by hand — the publish workflow runs `poetry version $TAG_NAME` from the tag.

## Tip — use subagents for protocol research

Spin up a `general-purpose` subagent whenever you need a second opinion on whether our v3 implementation matches the spec or the canonical reference. Brief it with the exact files/lines you're unsure about and what verdict you need; ask for citations back, not just a recommendation.

Tell the agent to use `octocode-mcp` (`githubViewRepoStructure`, `githubSearchCode`, `githubGetFileContent`, `githubSearchPullRequests`) for GitHub research. The three sources to point it at:

- **v3 protocol spec** — <https://inertiajs.com/docs/v3/core-concepts/the-protocol.md>
- **Laravel reference adapter** — <https://github.com/inertiajs/inertia-laravel/> (branch `3.x`); the canonical server-side implementation we mirror
- **Inertia core (client)** — <https://github.com/inertiajs/inertia/tree/3.x/packages/core>; what the client actually sends and expects on the wire

Use it for: clarifying ambiguous protocol wording, confirming a header/payload shape before changing `inertia/http.py`, or sanity-checking a fix against Laravel's `PropsResolver` / `Response` / `Directive`.
