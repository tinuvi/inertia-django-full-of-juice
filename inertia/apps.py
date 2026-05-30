import re
from collections.abc import Sequence
from typing import Any

from django.apps import AppConfig
from django.core import checks
from django.core.checks import CheckMessage

from .settings import settings


def check_ssr_exclude_patterns(
    app_configs: Sequence[AppConfig] | None, **kwargs: Any
) -> list[CheckMessage]:
    """Validate that every ``INERTIA_SSR_EXCLUDE`` entry is a compilable regex.

    Registered as a Django system check so a malformed pattern fails fast at
    startup (``runserver`` / ``manage.py check`` / ``migrate``) with an
    actionable message, instead of surfacing as a 500 on the first request
    whose path would have been tested against it.
    """
    errors: list[CheckMessage] = []
    for pattern in settings.INERTIA_SSR_EXCLUDE:
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(
                checks.Error(
                    f"INERTIA_SSR_EXCLUDE contains an invalid regex {pattern!r}: {exc}",
                    hint=(
                        "Each INERTIA_SSR_EXCLUDE entry must be a valid Python "
                        "regular expression — they are matched with re.search "
                        "against request.path."
                    ),
                    id="inertia.E001",
                )
            )
    return errors


class InertiaConfig(AppConfig):
    name = "inertia"

    def ready(self) -> None:
        checks.register(check_ssr_exclude_patterns)
