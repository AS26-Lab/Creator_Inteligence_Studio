from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefStructureView(BriefSectionView):
    section_title = "Structure"
    data_method = "list_outlines"
