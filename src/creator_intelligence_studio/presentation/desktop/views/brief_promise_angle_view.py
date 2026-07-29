from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefPromiseAngleView(BriefSectionView):
    section_title = "Promise & Angle"
    data_method = "list_promises"
