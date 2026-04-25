import warnings
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict as base_model_to_dict

from .prop_classes import (
    DeepMergeProp,
    DeferredProp,
    MergeProp,
    OnceProp,
    OptionalProp,
    PrependProp,
)

T = TypeVar("T")


def model_to_dict(model: models.Model) -> dict[str, Any]:
    return base_model_to_dict(model, exclude=("password",))


class InertiaJsonEncoder(DjangoJSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o.__class__, "InertiaMeta"):
            return {
                field: getattr(o, field) for field in o.__class__.InertiaMeta.fields
            }

        if isinstance(o, models.Model):
            return model_to_dict(o)

        if isinstance(o, QuerySet):
            return [
                (model_to_dict(obj) if isinstance(o.model, models.Model) else obj)
                for obj in o
            ]

        return super().default(o)


def lazy(prop: T | Callable[[], T]) -> OptionalProp[T]:
    warnings.warn(
        "lazy is deprecated and will be removed in a future version. Please use optional instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return optional(prop)


def optional(prop: T | Callable[[], T]) -> OptionalProp[T]:
    return OptionalProp(prop)


def defer(
    prop: T | Callable[[], T],
    group: str = "default",
    merge: bool = False,
    *,
    match_on: list[str] | None = None,
) -> DeferredProp[T]:
    return DeferredProp(prop, group=group, merge=merge, match_on=match_on)


def merge(
    prop: T | Callable[[], T],
    *,
    match_on: list[str] | None = None,
) -> MergeProp[T]:
    return MergeProp(prop, match_on=match_on)


def prepend(
    prop: T | Callable[[], T],
    *,
    match_on: list[str] | None = None,
) -> PrependProp[T]:
    return PrependProp(prop, match_on=match_on)


def deep_merge(
    prop: T | Callable[[], T],
    *,
    match_on: list[str] | None = None,
) -> DeepMergeProp[T]:
    return DeepMergeProp(prop, match_on=match_on)


def once(
    prop: T | Callable[[], T],
    *,
    key: str | None = None,
    fresh: bool = False,
    expires_in: timedelta | int | None = None,
    expires_at: datetime | int | None = None,
) -> OnceProp[T]:
    if expires_in is not None and expires_at is not None:
        raise ValueError("Provide only one of `expires_in` or `expires_at`, not both.")

    expires_at_ms: int | None = None

    if expires_in is not None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        if isinstance(expires_in, timedelta):
            expires_at_ms = now_ms + int(expires_in.total_seconds() * 1000)
        else:
            expires_at_ms = now_ms + expires_in * 1000
    elif expires_at is not None:
        if isinstance(expires_at, datetime):
            dt = (
                expires_at
                if expires_at.tzinfo is not None
                else expires_at.replace(tzinfo=timezone.utc)
            )
            expires_at_ms = int(dt.timestamp() * 1000)
        else:
            expires_at_ms = expires_at

    return OnceProp(prop, key=key, fresh=fresh, expires_at=expires_at_ms)
