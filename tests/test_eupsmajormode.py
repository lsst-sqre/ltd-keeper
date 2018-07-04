"""Unit tests for keeper.editiontracking.eupsmajormode.
"""

import pytest

from keeper.editiontracking.eupsmajormode import MajorReleaseTag


def test_parsing():
    tag = MajorReleaseTag('v1_0')
    assert tag.major == 1
    assert tag.minor == 0

    tag = MajorReleaseTag('v16_1')
    assert tag.major == 16
    assert tag.minor == 1

    with pytest.raises(ValueError):
        MajorReleaseTag('2_0')

    with pytest.raises(ValueError):
        MajorReleaseTag('v2')


def test_comparisons():
    assert MajorReleaseTag('v1_0') > MajorReleaseTag('v0_1')
    assert MajorReleaseTag('v1_0') != MajorReleaseTag('v0_1')

    assert MajorReleaseTag('v1_0') == MajorReleaseTag('v1_0')
    assert MajorReleaseTag('v1_0') >= MajorReleaseTag('v1_0')
