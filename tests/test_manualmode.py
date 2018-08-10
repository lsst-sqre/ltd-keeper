"""Test the manual tracking mode.
"""

from keeper.editiontracking.trackingmodes import EditionTrackingModes


def test_manual_mode():
    """Test the ManualTrackingMode.
    """
    modes = EditionTrackingModes()

    mode = modes['manual']

    assert mode.name == 'manual'

    # Never returns True, by definition
    assert mode.should_update(None, None) is False
