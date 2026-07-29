from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefDetailView(BriefSectionView):
    section_title = "Brief Detail"
    data_method = "list_briefs"
    scope = "creator"
