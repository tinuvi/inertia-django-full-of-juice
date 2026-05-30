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
- When you change the library, run the Playwright E2E flow against the dockerized sample before declaring the change complete:
    ```bash
    docker compose -f sample_project/docker-compose.yml up --build -d --wait
    (cd playwright_e2e && npm ci && npm run install-browsers && npm run test && npm run test:ssr)
    docker compose -f sample_project/docker-compose.yml down -v --remove-orphans
    ```
  See `playwright_e2e/README.md` for the full setup, the two service targets, and how the projects map.
- When the change adds or alters a v3 surface (headers, page-object fields, middleware behavior, prop kinds, SSR behavior), add or update a spec covering it in the same commit — put SSR-specific specs in `playwright_e2e/tests-ssr/`, the rest in `playwright_e2e/tests/`.
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

- Update `CHANGELOG.md` only when `./inertia/` (the library source) changes, but not including the `tests` folder. Use the active `[X.Y.Z]` heading and `Added` / `Changed` / `Fixed` / `Removed` subsections. Skip it for repo-tooling or sample-project edits.
- Update `README.md` when public API, install steps, or supported Python/Django versions change.
- Do **not** create new top-level docs (`*.md`) unless explicitly asked.

## Commits

- Use Conventional Commits.

## Deployment

- Releases are tag-driven via `.github/workflows/publish-package.yml`. Pushing an annotated tag matching the version number publishes to PyPI.
- Never edit `pyproject.toml`'s `version` by hand — the publish workflow runs `poetry version $TAG_NAME` from the tag.

## Tip — use subagents for protocol research

Brief the subagents on the specific files or lines in question and the feedback you need; they provide the analysis, and you make the final call.

- **`protocol-researcher`** — what the v3 spec and the `3.x` client core actually say. Use for ambiguous wording, header/payload shape, or wire-level questions.
- **`laravel-comparator`** — what the canonical Laravel adapter does.
- **`compliance-reviewer`** — pass/fail verdict on local diffs against both spec and Laravel reference.
