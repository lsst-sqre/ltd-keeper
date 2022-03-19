"""Implements the ``git_ref`` tracking mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from keeper.editiontracking.base import TrackingModeBase

if TYPE_CHECKING:
    from keeper.models import Build, Edition

__all__ = ["GitRefsTrackingMode"]


class GitRefsTrackingMode(TrackingModeBase):
    """Tracking mode where an edition tracks an array of Git refs.

    This is the default mode if Edition.mode is None.
    """

    @property
    def name(self) -> str:
        return "git_refs"

    def should_update(
        self, edition: Optional[Edition], candidate_build: Optional[Build]
    ) -> bool:
        if edition is None or candidate_build is None:
            return False

        if (candidate_build.product == edition.product) and (
            candidate_build.git_refs == edition.tracked_refs
        ):
            return True
        else:
            return False
