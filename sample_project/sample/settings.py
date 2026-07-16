import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "django-insecure-sample-key-not-for-production"
)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_vite",
    "inertia",
    "sample.apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "inertia.middleware.InertiaMiddleware",
    "sample.apps.core.middleware.ShareDemoMiddleware",
]

ROOT_URLCONF = "sample.urls"
WSGI_APPLICATION = "sample.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
_VITE_DIST = BASE_DIR / "frontend" / "dist"
STATICFILES_DIRS = [_VITE_DIST] if _VITE_DIST.exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DJANGO_VITE = {
    "default": {
        # Defaults to DEBUG (Vite dev server) but can be forced off so a
        # container serves the built manifest while still running with DEBUG=True
        # (so runserver serves the hashed assets from frontend/dist).
        "dev_mode": os.getenv("DJANGO_VITE_DEV_MODE", str(DEBUG)).lower() == "true",
        "dev_server_host": os.getenv("DJANGO_VITE_DEV_SERVER_HOST", "localhost"),
        "dev_server_port": int(os.getenv("DJANGO_VITE_DEV_SERVER_PORT", "5173")),
        "manifest_path": BASE_DIR / "frontend" / "dist" / "manifest.json",
    }
}

INERTIA_LAYOUT = "base.html"
INERTIA_SSR_ENABLED = os.getenv("INERTIA_SSR_ENABLED", "False").lower() == "true"
INERTIA_SSR_URL = os.getenv("INERTIA_SSR_URL", "http://localhost:13714")
# Comma-separated regex patterns; matching request paths skip SSR.
INERTIA_SSR_EXCLUDE = [p for p in os.getenv("INERTIA_SSR_EXCLUDE", "").split(",") if p]
# --- E2E test hooks: runtime-mutable asset version --------------------------
# INERTIA_VERSION is a callable (the library resolves it per request) so the
# Playwright suite can flip the server's asset version while the container is
# running and prove the v3.6 background-vs-sync 409 behavior. The override is
# file-backed — cross-worker safe, every process reads the same file — and
# falls back to the env default when the file is absent or empty.
E2E_TEST_HOOKS = os.getenv("E2E_TEST_HOOKS", "False").lower() == "true"
E2E_VERSION_OVERRIDE_FILE = os.getenv(
    "E2E_VERSION_OVERRIDE_FILE", "/tmp/inertia_e2e_version_override"
)
_INERTIA_VERSION_DEFAULT = os.getenv("INERTIA_VERSION", "1.0")


def _resolve_inertia_version() -> str:
    # Sync only (house no-async rule). Reads a tiny file a few times per
    # request — fine for the sample; production users set a plain string.
    try:
        override = Path(E2E_VERSION_OVERRIDE_FILE).read_text().strip()
    except OSError:
        override = ""
    return override or _INERTIA_VERSION_DEFAULT


INERTIA_VERSION = _resolve_inertia_version

# Surface every protocol decision the library makes so that exercising the
# sample app against runserver shows the library's reasoning in the same
# terminal as the request log line. Keep this on for the sample project;
# production users opt in via their own LOGGING config.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "inertia_e2e": {
            "format": "[inertia] %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "inertia_console": {
            "class": "logging.StreamHandler",
            "formatter": "inertia_e2e",
        },
    },
    "loggers": {
        "inertia_django_full_of_juice": {
            "handlers": ["inertia_console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
