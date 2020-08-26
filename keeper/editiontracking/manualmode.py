"""Mode that does not automatically update an edition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.editiontracking.base import TrackingModeBase

if TYPE_CHECKING:
    from keeper.models import Build, Edition

__all__ = ["ManualTrackingMode"]


class ManualTrackingMode(TrackingModeBase):
    """Tracking mode that does not track (requires that an edition's build_url
    be manually updated to update the edition).
    """

    @property
    def name(self) -> str:
        return "manual"

    def should_update(
        self, edition: Optional[Edition], candidate_build: Optional[Build]
    ) -> bool:
        return False
