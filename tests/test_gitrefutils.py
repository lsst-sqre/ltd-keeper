"""Tests for the app.gitrefutils module.
"""

import pytest

from app.gitrefutils import LsstDocVersionTag


def test_lsst_doc_tag():
    version = LsstDocVersionTag('v1.2')

    assert version.major == 1
    assert version.minor == 2


def test_invalid_lsst_doc_tag():
    with pytest.raises(ValueError):
        LsstDocVersionTag('1.2')
