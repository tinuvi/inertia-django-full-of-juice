from collections.abc import Callable
from typing import Any, Union

from django.conf import settings as django_settings
from urllib3.util import Timeout as Urllib3Timeout

from .utils import InertiaJsonEncoder

__all__ = ["settings", "resolve_inertia_version"]

# The v3 page-object ``version`` field is ``string|number`` on the wire, but the
# client core narrows it to ``string | null``. ``INERTIA_VERSION`` may therefore
# be a plain value or a zero-arg callable (the Django equivalent of Laravel's
# version closure) — e.g. one that returns the staticfiles manifest hash so the
# version auto-busts on every deploy. It is resolved to a string per request by
# ``resolve_inertia_version``.
VersionValue = Union[str, int, float, None]
VersionResolver = Callable[[], VersionValue]

# ``INERTIA_SSR_TIMEOUT`` is passed verbatim to ``requests``: seconds as a number
# (applied to both the connect and the read phase), a ``(connect, read)`` pair,
# a urllib3 ``Timeout`` (e.g. ``total=`` to cap the whole transfer), or ``None``
# to wait forever. Validated at startup by the ``inertia.E002`` check.
SsrTimeout = Union[float, tuple[float, float], Urllib3Timeout, None]


class InertiaSettings:
    INERTIA_VERSION: Union[VersionValue, VersionResolver] = "1.0"
    INERTIA_JSON_ENCODER = InertiaJsonEncoder
    INERTIA_SSR_URL = "http://localhost:13714"
    INERTIA_SSR_ENABLED = False
    INERTIA_SSR_EXCLUDE: list[str] = []
    # Bounds the first-load render call so a hung SSR service degrades to the
    # client-side shell instead of stalling the request. Mirrors Laravel's
    # ``inertia.ssr.timeout`` (``INERTIA_SSR_TIMEOUT``); unlike Laravel, whose
    # HTTP client already defaults to 30s, ``requests`` has no default at all,
    # so the library ships a finite one. 5s matches the official SSR docs example.
    INERTIA_SSR_TIMEOUT: SsrTimeout = 5.0
    INERTIA_ENCRYPT_HISTORY = False
    # Mirrors Laravel's ``inertia.expose_shared_prop_keys`` (default true): emit
    # the v3 ``sharedProps`` page field listing the top-level keys registered
    # via ``share()`` so the client can carry them over during instant visits.
    INERTIA_EXPOSE_SHARED_PROP_KEYS = True
    # Opt-in bridge: drain ``django.contrib.messages`` into the v3 ``flash``
    # page field (under the reserved ``messages`` key) at render time.
    INERTIA_FLASH_FROM_MESSAGES = False

    def __getattribute__(self, name: str) -> Any:
        try:
            return getattr(django_settings, name)
        except AttributeError:
            return super().__getattribute__(name)


settings = InertiaSettings()


def resolve_inertia_version() -> str:
    """Resolve ``INERTIA_VERSION`` into the wire string emitted in the page object
    and compared against the ``X-Inertia-Version`` request header.

    Mirrors Laravel's ``ResponseFactory::getVersion(): string`` (``3.x``):
    a callable is invoked (Laravel resolves the closure), then the result is cast
    to ``str``. ``None`` resolves to ``""`` so that, like Laravel's
    ``(string) null``, an unset version disables asset versioning — the v3 client
    omits the ``X-Inertia-Version`` header whenever ``page.version`` is falsy.
    """
    version = settings.INERTIA_VERSION
    if callable(version):
        version = version()
    if version is None:
        return ""
    return str(version)
