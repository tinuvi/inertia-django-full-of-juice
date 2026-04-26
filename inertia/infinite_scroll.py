from collections.abc import Callable
from typing import Any, TypeVar

from django.http import HttpRequest

from .prop_classes import CallableProp, MergeableProp, MergeStrategy

T = TypeVar("T")


class InfiniteScrollProp(CallableProp[T], MergeableProp):
    """A prop that participates in v3 infinite-scroll merge intent.

    The merge strategy (``append`` vs ``prepend``) is selected at render
    time from the ``X-Inertia-Infinite-Scroll-Merge-Intent`` request
    header. When the header is missing or holds an unrecognized value,
    the prop falls back to ``append``.

    The Django ``HttpRequest`` is passed in explicitly because Django
    does not expose an implicit "current request" the way Laravel does.
    Callers must supply the same request object that the surrounding
    view received so that the prop can read the merge-intent header at
    resolution time.

    Pagination metadata (``page_name``, ``previous_page``, ``next_page``,
    ``current_page``) is supplied by the caller. This module deliberately
    keeps itself a pure protocol primitive: it does not know about
    ``django.core.paginator.Paginator`` or any other paging abstraction.
    The caller is expected to compute these values server-side and pass
    them in.
    """

    def __init__(
        self,
        prop: T | Callable[[], T],
        request: HttpRequest,
        *,
        page_name: str = "page",
        previous_page: int | str | None = None,
        next_page: int | str | None = None,
        current_page: int | str | None = None,
        match_on: list[str] | None = None,
    ) -> None:
        super().__init__(prop)
        self._request = request
        self.page_name = page_name
        self.previous_page = previous_page
        self.next_page = next_page
        self.current_page = current_page
        self._match_on = list(match_on) if match_on else []

    def should_merge(self) -> bool:
        return True

    def merge_strategy(self) -> MergeStrategy:
        intent = self._request.headers.get("X-Inertia-Infinite-Scroll-Merge-Intent", "")
        return "prepend" if intent == "prepend" else "append"

    def match_on(self) -> list[str]:
        return list(self._match_on)

    def scroll_metadata(self) -> dict[str, Any]:
        return {
            "pageName": self.page_name,
            "previousPage": self.previous_page,
            "nextPage": self.next_page,
            "currentPage": self.current_page,
        }


def infinite_scroll(
    prop: T | Callable[[], T],
    request: HttpRequest,
    *,
    page_name: str = "page",
    previous_page: int | str | None = None,
    next_page: int | str | None = None,
    current_page: int | str | None = None,
    match_on: list[str] | None = None,
) -> InfiniteScrollProp[T]:
    """Build an :class:`InfiniteScrollProp` for the v3 infinite-scroll flow.

    The ``request`` parameter is required: the prop reads the
    ``X-Inertia-Infinite-Scroll-Merge-Intent`` header at render time to
    decide whether the prop is appended (default) or prepended. Pass the
    same ``HttpRequest`` instance the surrounding view received.

    Pagination metadata is opaque to this helper. Compute
    ``previous_page``, ``next_page``, ``current_page``, and (optionally)
    a custom ``page_name`` server-side and hand the values in. The
    helper does not peek at Django's ``Paginator`` or any other paging
    abstraction.
    """
    return InfiniteScrollProp(
        prop,
        request,
        page_name=page_name,
        previous_page=previous_page,
        next_page=next_page,
        current_page=current_page,
        match_on=match_on,
    )
