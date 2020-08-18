"""Implements the ``git_ref`` tracking mode.
"""

__all__ = ('GitRefTrackingMode',)


class GitRefTrackingMode:
    """Default tracking mode where an edition tracks an array of Git refs.

    This is the default mode if Edition.mode is None.
    """

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'git_refs'

    def should_update(self, edition, candidate_build):
        if (candidate_build.product == edition.product) \
                and (candidate_build.git_refs == edition.tracked_refs):
            return True
        else:
            return False
