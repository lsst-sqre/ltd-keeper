"""Implement the "eups_major_release" Edition tracking mode.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional, Tuple

from keeper.editiontracking.base import TrackingModeBase

if TYPE_CHECKING:
    from keeper.models import Build, Edition

TAG_PATTERN = re.compile(r"^v(?P<major>\d+)_(?P<minor>\d+)$")
"""Regular expression for matching an EUPS major release tag with the format
``vX_Y``.
"""

GIT_TAG_PATTERN = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)$")
"""Regular expression for matching the Git-version of an EUPS major release tag
with the format ``X.Y``.
"""

__all__ = ["EupsMajorReleaseTrackingMode"]


class EupsMajorReleaseTrackingMode(TrackingModeBase):
    """Tracking mode for the the newest EUPS major release (``vX_Y`` or
    ``X.Y``).
    """

    @property
    def name(self) -> str:
        return "eups_major_release"

    def should_update(
        self, edition: Optional[Edition], candidate_build: Optional[Build]
    ) -> bool:
        if edition is None or candidate_build is None:
            return False

        # Does the build have a major release tag?
        try:
            candidate_version = MajorReleaseTag(candidate_build.git_refs[0])
        except ValueError:
            return False

        # Does the edition's current build have a major release?
        # as its Git ref?
        try:
            current_version = MajorReleaseTag(edition.build.git_refs[0])
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


class MajorReleaseTag:
    """An EUPS tag for a major release."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        match = TAG_PATTERN.search(tag)
        if match is None:
            # Fall back to git variant
            match = GIT_TAG_PATTERN.search(tag)
            if match is None:
                raise ValueError(
                    "{!r} is not an EUPS major release tag ".format(tag)
                )
        self.major = int(match.group("major"))
        self.minor = int(match.group("minor"))

    @property
    def parts(self) -> Tuple[int, int]:
        return (self.major, self.minor)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MajorReleaseTag):
            raise NotImplementedError

        return self.parts == other.parts

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, MajorReleaseTag):
            raise NotImplementedError

        return self.__eq__(other) is False

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, MajorReleaseTag):
            raise NotImplementedError

        return self.parts > other.parts

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, MajorReleaseTag):
            raise NotImplementedError

        return (self.__eq__(other) is False) and (self.__gt__(other) is False)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, MajorReleaseTag):
            raise NotImplementedError

        return (self.__eq__(other) is True) or (self.__gt__(other) is True)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, MajorReleaseTag):
            raise NotImplementedError

        return (self.__eq__(other) is True) or (self.__gt__(other) is False)
