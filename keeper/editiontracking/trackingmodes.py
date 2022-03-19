from __future__ import annotations

from typing import Union

from keeper.editiontracking.base import TrackingModeBase
from keeper.editiontracking.eupsdailymode import EupsDailyReleaseTrackingMode
from keeper.editiontracking.eupsmajormode import EupsMajorReleaseTrackingMode
from keeper.editiontracking.eupsweeklymode import EupsWeeklyReleaseTrackingMode
from keeper.editiontracking.gitrefsmode import GitRefsTrackingMode
from keeper.editiontracking.lsstdocmode import LsstDocTrackingMode
from keeper.editiontracking.manualmode import ManualTrackingMode
from keeper.exceptions import ValidationError

__all__ = ["EditionTrackingModes"]


class EditionTrackingModes:
    """Collection of edition tracking mode objects.

    These modes determine how an edition should be updated with new builds.
    """

    _modes = {
        1: GitRefsTrackingMode(),
        2: LsstDocTrackingMode(),
        3: EupsMajorReleaseTrackingMode(),
        4: EupsWeeklyReleaseTrackingMode(),
        5: EupsDailyReleaseTrackingMode(),
        6: ManualTrackingMode(),
    }
    """Map of tracking mode ID (an integer stored in the DB to the tracking
    mode instance that can evaluate whether an edition should be updated
    based on its own logic.
    """

    _name_map = {mode.name: _id for _id, mode in _modes.items()}
    """Map of mode names to DB IDs.

    This is the inverse of ``_modes``.
    """

    def __getitem__(self, key: Union[int, str]) -> TrackingModeBase:
        if not isinstance(key, int):
            key = self.name_to_id(key)
        return self._modes[key]

    def __contains__(self, name: str) -> bool:
        """Check if name is one of the tracking modes."""
        if name in self._name_map.keys():
            return True
        else:
            return False

    def name_to_id(self, mode: str) -> int:
        """Convert a mode name (string used by the web API) to a mode ID
        (integer) used by the DB.

        Parameters
        ----------
        mode : `str`
            Mode name.

        Returns
        -------
        mode_id : `int`
            Mode ID.

        Raises
        ------
        ValidationError
            Raised if ``mode`` is unknown.
        """
        try:
            mode_id = self._name_map[mode]
        except KeyError:
            message = (
                "Edition tracking mode {!r} unknown. Valid values " "are {!r}"
            )
            raise ValidationError(message.format(mode, self._name_map.keys()))
        return mode_id

    def id_to_name(self, mode_id: int) -> str:
        """Convert a mode ID (integer used by the DB) to a name used by the
        web API.

        Parameters
        ----------
        mode_id : `int`
            Mode ID.

        Returns
        -------
        mode : `str`
            Mode name.

        Raises
        ------
        ValidationError
            Raised if ``mode`` is unknown.
        """
        try:
            mode = self._modes[mode_id]
        except KeyError:
            message = (
                "Edition tracking mode ID {!r} unknown. Valid values "
                "are {!r}"
            )
            raise ValidationError(message.format(mode_id, self._modes.keys()))
        return mode.name
