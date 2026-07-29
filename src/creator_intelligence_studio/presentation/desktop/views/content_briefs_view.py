from __future__ import annotations

from .briefs_base_view import BriefSectionView


class ContentBriefsView(BriefSectionView):
    section_title = "Briefs"
    data_method = "list_briefs"
    scope = "creator"
