"""Implement the "eups_daily_release" Edition tracking mode."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional, Tuple

from structlog import get_logger

from keeper.editiontracking.base import TrackingModeBase

if TYPE_CHECKING:
    from keeper.models import Build, Edition

__all__ = ["EupsDailyReleaseTrackingMode"]

TAG_PATTERN = re.compile(r"^d_(?P<year>\d+)_(?P<month>\d+)_(?P<day>\d+)$")
"""Regular expression for matching an EUPS daily release tag with the format
``d_YYYY_MM_DD``.
"""

GIT_TAG_PATTERN = re.compile(
    r"^d\.(?P<year>\d+)\.(?P<month>\d+)\.(?P<day>\d+)$"
)
"""Regular expression for matching the Git variant of an EUPS daily release tag
with the format ``d.YYYY.MM.DD``.
"""


class EupsDailyReleaseTrackingMode(TrackingModeBase):
    """Tracking mode for the the newest EUPS daily release (``d_YYYY_MM_DD``
    of ``d.YYYY.MM.DD``).
    """

    @property
    def name(self) -> str:
        return "eups_daily_release"

    def should_update(
        self, edition: Optional[Edition], candidate_build: Optional[Build]
    ) -> bool:
        if edition is None or candidate_build is None:
            return False

        # Does the build have a daily release tag?
        try:
            candidate_version = DailyReleaseTag(candidate_build.git_refs[0])
        except ValueError:
            return False

        # Does the edition's current build have a daily release
        # as its Git ref?
        try:
            current_version = DailyReleaseTag(edition.build.git_refs[0])
        except (ValueError, AttributeError):
            # Attribute error if current build is None
            # Not currently tracking a version, so automatically accept
            # the candidate.
            return True

        # Is the candidate version newer than the existing version?
        if candidate_version >= current_version:
            # Accept >= in case a replacement of the same version is
            # somehow required.
            return True

        return False


class DailyReleaseTag:
    """An EUPS tag for a daily release."""

    def __init__(self, tag: str) -> None:
        self.logger = get_logger(__name__)

        self.logger.debug("DailyReleaseTag", tag=tag)

        self.tag = tag
        match = TAG_PATTERN.search(tag)
        if match is None:
            # Fall back to Git variant pattern
            match = GIT_TAG_PATTERN.search(tag)
            if match is None:
                raise ValueError(
                    "{!r} is not an EUPS daily release tag ".format(tag)
                )
        self.year = int(match.group("year"))
        self.month = int(match.group("month"))
        self.day = int(match.group("day"))

        self.logger.debug(
            "DailyReleaseTag", tag=tag, year=self.year, day=self.day
        )

    @property
    def parts(self) -> Tuple[int, int, int]:
        return (self.year, self.month, self.day)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DailyReleaseTag):
            raise NotImplementedError
        return self.parts == other.parts

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, DailyReleaseTag):
            raise NotImplementedError
        return self.__eq__(other) is False

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, DailyReleaseTag):
            raise NotImplementedError
        return self.parts > other.parts

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DailyReleaseTag):
            raise NotImplementedError
        return (self.__eq__(other) is False) and (self.__gt__(other) is False)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, DailyReleaseTag):
            raise NotImplementedError
        return (self.__eq__(other) is True) or (self.__gt__(other) is True)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, DailyReleaseTag):
            raise NotImplementedError
        return (self.__eq__(other) is True) or (self.__gt__(other) is False)
