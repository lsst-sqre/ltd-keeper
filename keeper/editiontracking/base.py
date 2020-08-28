from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from keeper.models import Build, Edition

__all__ = ["TrackingModeBase"]


class TrackingModeBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def should_update(
        self, edition: Optional[Edition], candidate_build: Optional[Build]
    ) -> bool:
        pass
