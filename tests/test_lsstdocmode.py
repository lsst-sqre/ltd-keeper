"""Tests for the keeper.editiontracking.lsstdocmode module."""

import pytest

from keeper.editiontracking.lsstdocmode import LsstDocVersionTag


def test_lsst_doc_tag() -> None:
    version = LsstDocVersionTag("v1.2")

    assert version.major == 1
    assert version.minor == 2


def test_invalid_lsst_doc_tag() -> None:
    with pytest.raises(ValueError):
        LsstDocVersionTag("1.2")
