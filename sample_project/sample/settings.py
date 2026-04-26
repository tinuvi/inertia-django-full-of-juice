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
        "dev_mode": DEBUG,
        "dev_server_host": os.getenv("DJANGO_VITE_DEV_SERVER_HOST", "localhost"),
        "dev_server_port": int(os.getenv("DJANGO_VITE_DEV_SERVER_PORT", "5173")),
        "manifest_path": BASE_DIR / "frontend" / "dist" / "manifest.json",
    }
}

INERTIA_LAYOUT = "base.html"
INERTIA_SSR_ENABLED = os.getenv("INERTIA_SSR_ENABLED", "False").lower() == "true"
INERTIA_SSR_URL = os.getenv("INERTIA_SSR_URL", "http://localhost:13714")
INERTIA_VERSION = os.getenv("INERTIA_VERSION", "1.0")
