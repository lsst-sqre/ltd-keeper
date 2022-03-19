"""Implements the ``git_ref`` tracking mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.editiontracking.base import TrackingModeBase

if TYPE_CHECKING:
    from keeper.models import Build, Edition

__all__ = ["GitRefTrackingMode"]


class GitRefTrackingMode(TrackingModeBase):
    """Tracking mode where an edition tracks a given git_ref (commonly
    a branch).
    """

    @property
    def name(self) -> str:
        return "git_ref"

    def should_update(
        self, edition: Optional[Edition], candidate_build: Optional[Build]
    ) -> bool:
        if edition is None or candidate_build is None:
            return False

        if (candidate_build.product == edition.product) and (
            candidate_build.git_ref == edition.tracked_ref
        ):
            return True
        else:
            return False
