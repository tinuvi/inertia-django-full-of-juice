# syntax=docker/dockerfile:1
# Build context is the repo root (see sample_project/docker-compose.yml) so the
# image can install the library itself as the editable path dependency `../`.

# --- Stage 1: build the client bundle (manifest + hashed assets) ---
FROM node:22-slim AS frontend
WORKDIR /build
COPY sample_project/package.json sample_project/package-lock.json ./
RUN npm ci
COPY sample_project/ ./
RUN npm run build

# --- Stage 2: Django web ---
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /src
RUN pip install --upgrade pip && pip install "poetry>=2,<3"

# Library source — resolves the sample's `inertia-django-full-of-juice = {path="../"}`.
COPY pyproject.toml poetry.lock README.md LICENSE ./
COPY inertia ./inertia

# Sample project + its Python deps (django, django-vite, editable library).
COPY sample_project ./sample_project
WORKDIR /src/sample_project
RUN poetry install --no-interaction

# Built client assets from stage 1 (django_vite production mode reads the manifest).
COPY --from=frontend /build/frontend/dist ./frontend/dist
RUN chmod +x ./scripts/*.sh

CMD ["./scripts/start-web.sh"]
