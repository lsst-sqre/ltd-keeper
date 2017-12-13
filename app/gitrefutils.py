"""Utilities for parsing Git refs according to LSST format."""

__all__ = ['DOCUSHARE_PATTERN', 'LSST_DOC_V_TAG', 'LsstDocVersionTag']

import re


# The RFC-401 format for tagged docushare releases.
DOCUSHARE_PATTERN = re.compile(r'docushare-v(?P<version>[\d\.]+)')

# The RFC-405/LPM-51 format for LSST semantic document versions.
# v<minor>.<major>
LSST_DOC_V_TAG = re.compile(r'^v(?P<major>[\d+])\.(?P<minor>[\d+])$')


class LsstDocVersionTag(object):
    """Represent and compare LSST document (``v<major>.<minor>``) version
    tags.

    These semantic version tags are defined in LPM-51.

    Parameters
    ----------
    version_str : `str`
        Tag name. To be parsed successfully, the tag must be formatted as
        ``'v<major>.<minor>'``.

    Raises
    ------
    ValueError
        Raised if the ``version_str`` argument cannot be parsed (it doesn't
        match the LPM-51 standard).
    """

    def __init__(self, version_str):
        super(LsstDocVersionTag, self).__init__()
        self.version_str = version_str
        match = LSST_DOC_V_TAG.match(version_str)
        if match is None:
            raise ValueError(
                '{:r} is not a LSST document version tag'.format(version_str))
        self.major = int(match.group('major'))
        self.minor = int(match.group('minor'))

    def __repr__(self):
        return 'LsstDocVersion({:r})'.format(self.version_str)

    def __str__(self):
        return '{0:d}.{1:d}'.format(self.major, self.minor)

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor

    def __ne__(self, other):
        return self.__eq__(other) is False

    def __gt__(self, other):
        if self.major > other.major:
            return True
        elif self.major == other.major:
            return self.minor > other.minor
        else:
            return False

    def __lt__(self, other):
        return (self.__eq__(other) is False) and (self.__gt__(other) is False)

    def __ge__(self, other):
        return (self.__eq__(other) is True) or (self.__gt__(other) is True)

    def __le__(self, other):
        return (self.__eq__(other) is True) or (self.__gt__(other) is False)
