"""Generic page-of-results container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """A single page of items plus meta-data."""

    items: Sequence[T]
    total: int           # total items in the whole result set
    pages: int           # total number of pages
    page: int            # current page index (1-based)

    per_page: int        # size of each page (for convenience)

    # ------------- helpers -------------
    def has_next(self) -> bool:
        return self.page < self.pages

    def has_prev(self) -> bool:
        return self.page > 1
