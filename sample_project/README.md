# Sample project

Thin Django + React app that exercises the features of `inertia-django-full-of-juice`. Backend uses a path dependency on the sibling `inertia` package, so any change to the library is picked up immediately.

## Requirements

- Python 3.12+
- Node 20+

## Backend

From `sample_project/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry config --local virtualenvs.in-project true
poetry env use .venv/bin/python
poetry install --no-root
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Django listens on http://localhost:8000.

## Frontend

In a second terminal, from `sample_project/`:

```bash
npm install
npm run dev
```

Vite listens on http://localhost:5173 and is wired into Django via `django-vite` (HMR in dev, manifest in prod).

## Lint & format (frontend)

```bash
npm run lint            # biome check frontend
npm run format          # biome format --write frontend
```

Run `format` before `lint` if biome reports formatter diffs.

## Production build

```bash
npm run build           # client bundle → frontend/dist/
npm run build-ssr       # SSR bundle  → frontend/dist/ssr.js
```

To enable SSR at runtime: `INERTIA_SSR_ENABLED=true` and run `node frontend/dist/ssr.js` (defaults to port 13714).

## What the sample exercises

| Page  | URL          | Library features                                         |
|-------|--------------|----------------------------------------------------------|
| Home  | `/`          | `share()`, `@inertia` decorator, plain props             |
| Lazy  | `/lazy/`     | `optional()`, `defer()` (incl. group), `once()`          |
| Lists | `/lists/`    | `merge()` + `match_on`, `prepend()`, `deep_merge()`      |
| Feed  | `/feed/`     | `infinite_scroll()` with `current_page`/`next_page`      |
| Form  | `/form/`     | `errors_response()`, `inertia_redirect()`                |
| —     | `/redirect-fragment/` | `preserve_fragment()`                           |
