"""Mode that does not automatically update an edition.
"""

__all__ = ("ManualTrackingMode",)


class ManualTrackingMode:
    """Tracking mode that does not track (requires that an edition's build_url
    be manually updated to update the edition).
    """

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "manual"

    def should_update(self, edition, candidate_build):
        return False
