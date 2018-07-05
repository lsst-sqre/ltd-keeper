"""Implement the "eups_weekly_release" Edition tracking mode.
"""

__all__ = ('EupsWeeklyReleaseTrackingMode',)

import re
from structlog import get_logger


TAG_PATTERN = re.compile(r'^w_(?P<year>\d+)_(?P<week>\d+)$')
"""Regular expression for matching an EUPS weekly release tag with the format
``w_YYYY_WW``.
"""


class EupsWeeklyReleaseTrackingMode:
    """Tracking mode for the the newest EUPS weekly release (``w_YYYY_WW``).
    """

    @property
    def name(self):
        return 'eups_weekly_release'

    def should_update(self, edition, candidate_build):
        # Does the build have the w_YYYY_WW tag?
        try:
            candidate_version = WeeklyReleaseTag(
                candidate_build.git_refs[0])
        except ValueError:
            return False

        # Does the edition's current build have a weekly release
        # as its Git ref?
        try:
            current_version = WeeklyReleaseTag(
                edition.build.git_refs[0])
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


class WeeklyReleaseTag:
    """An EUPS tag for a weekly release.
    """

    def __init__(self, tag):
        self.logger = get_logger(__name__)

        self.logger.debug('WeeklyReleaseTag', tag=tag)

        self.tag = tag
        match = TAG_PATTERN.search(tag)
        if match is None:
            raise ValueError(
                '{!r} is not an EUPS weekly release tag '.format(tag))
        self.year = int(match.group('year'))
        self.week = int(match.group('week'))

        self.logger.debug('WeeklyReleaseTag',
                          tag=tag, year=self.year, week=self.week)

    @property
    def parts(self):
        return (self.year, self.week)

    def __eq__(self, other):
        return self.parts == other.parts

    def __ne__(self, other):
        return self.__eq__(other) is False

    def __gt__(self, other):
        return self.parts > other.parts

    def __lt__(self, other):
        return (self.__eq__(other) is False) and (self.__gt__(other) is False)

    def __ge__(self, other):
        return (self.__eq__(other) is True) or (self.__gt__(other) is True)

    def __le__(self, other):
        return (self.__eq__(other) is True) or (self.__gt__(other) is False)
