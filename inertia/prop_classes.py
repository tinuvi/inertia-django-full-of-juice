from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, Literal, TypeVar

T = TypeVar("T")

MergeStrategy = Literal["append", "prepend", "deep"]


class CallableProp(Generic[T]):
    def __init__(self, prop: T | Callable[[], T]) -> None:
        self.prop = prop

    def __call__(self) -> T:
        return self.prop() if callable(self.prop) else self.prop


class MergeableProp(ABC):
    @abstractmethod
    def should_merge(self) -> bool:
        pass

    def merge_strategy(self) -> MergeStrategy:
        return "append"

    def match_on(self) -> list[str]:
        """Dot-paths under this prop to dedup on (e.g. ['id', 'data.id'])."""
        return []


class IgnoreOnFirstLoadProp:
    pass


class OptionalProp(CallableProp[T], IgnoreOnFirstLoadProp):
    pass


class DeferredProp(CallableProp[T], MergeableProp, IgnoreOnFirstLoadProp):
    def __init__(
        self,
        prop: T | Callable[[], T],
        group: str,
        merge: bool = False,
        *,
        match_on: list[str] | None = None,
    ) -> None:
        super().__init__(prop)
        self.group = group
        self.merge = merge
        self._match_on = list(match_on) if match_on else []

    def should_merge(self) -> bool:
        return self.merge

    def match_on(self) -> list[str]:
        return list(self._match_on)


class MergeProp(CallableProp[T], MergeableProp):
    def __init__(
        self,
        prop: T | Callable[[], T],
        *,
        match_on: list[str] | None = None,
    ) -> None:
        super().__init__(prop)
        self._match_on = list(match_on) if match_on else []

    def should_merge(self) -> bool:
        return True

    def match_on(self) -> list[str]:
        return list(self._match_on)


class PrependProp(CallableProp[T], MergeableProp):
    def __init__(
        self,
        prop: T | Callable[[], T],
        *,
        match_on: list[str] | None = None,
    ) -> None:
        super().__init__(prop)
        self._match_on = list(match_on) if match_on else []

    def should_merge(self) -> bool:
        return True

    def merge_strategy(self) -> MergeStrategy:
        return "prepend"

    def match_on(self) -> list[str]:
        return list(self._match_on)


class DeepMergeProp(CallableProp[T], MergeableProp):
    def __init__(
        self,
        prop: T | Callable[[], T],
        *,
        match_on: list[str] | None = None,
    ) -> None:
        super().__init__(prop)
        self._match_on = list(match_on) if match_on else []

    def should_merge(self) -> bool:
        return True

    def merge_strategy(self) -> MergeStrategy:
        return "deep"

    def match_on(self) -> list[str]:
        return list(self._match_on)


class OnceProp(CallableProp[T]):
    def __init__(
        self,
        prop: T | Callable[[], T],
        *,
        key: str | None = None,
        fresh: bool = False,
        expires_at: int | None = None,
    ) -> None:
        super().__init__(prop)
        self.key = key
        self.fresh = fresh
        self.expires_at = expires_at
