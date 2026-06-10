from typing import Any

from django.contrib.messages import get_messages
from django.http import HttpRequest

from inertia import share


def _consume_django_messages(request: HttpRequest) -> list[dict[str, Any]]:
    """Drain ``django.contrib.messages`` into a JSON-friendly list.

    Iterating ``get_messages`` marks the storage as used, so each message
    rides on exactly one response — Django itself provides the one-shot
    (flash) semantics, which is why the library ships no ``flash`` page
    field.
    """
    return [
        {
            "message": message.message,
            "level": message.level,
            "tags": message.tags,
            "extra_tags": message.extra_tags,
            "level_tag": message.level_tag,
        }
        for message in get_messages(request)
    ]


class ShareDemoMiddleware:
    """Cross-cutting props injected on every Inertia response via `share()`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        share(
            request,
            app_name="Inertia Django Sample",
            user=lambda: {
                "name": "Brandon",
                "role": "goalie",
            },
            messages=_consume_django_messages(request),
        )
        return self.get_response(request)
