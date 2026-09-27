import math
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


def _is_valid_timeout_part(value: object) -> bool:
    if value is None:
        return True
    # ``bool`` is an ``int`` subclass, but urllib3 rejects it explicitly.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    # ``inf`` passes urllib3's own validation, then overflows the platform clock
    # on every call; ``None`` is the way to wait forever. ``nan`` fails ``> 0``.
    return math.isfinite(value) and value > 0


def check_ssr_timeout(
    app_configs: Sequence[AppConfig] | None, **kwargs: Any
) -> list[CheckMessage]:
    """Validate ``INERTIA_SSR_TIMEOUT`` against what ``requests`` accepts.

    urllib3 rejects a malformed timeout with ``ValueError`` on every render
    call, which the SSR fallback catches — so without this check a typo such as
    ``"4"`` (an unparsed env var) silently disables SSR on every request instead
    of failing when Django runs its checks (``runserver`` / ``manage.py check``
    / ``migrate``).
    """
    timeout = settings.INERTIA_SSR_TIMEOUT
    if isinstance(timeout, tuple):
        valid = len(timeout) == 2 and all(_is_valid_timeout_part(p) for p in timeout)
    else:
        valid = _is_valid_timeout_part(timeout)
    if valid:
        return []
    return [
        checks.Error(
            f"INERTIA_SSR_TIMEOUT must be a positive, finite number of seconds, "
            f"a (connect, read) tuple of them, or None; got {timeout!r}.",
            hint=(
                "The value is passed verbatim as the requests timeout of the SSR "
                "render call. Convert env vars with float() before assigning them, "
                "and use None (not inf) to wait forever."
            ),
            id="inertia.E002",
        )
    ]


class InertiaConfig(AppConfig):
    name = "inertia"

    def ready(self) -> None:
        checks.register(check_ssr_exclude_patterns)
        checks.register(check_ssr_timeout)
