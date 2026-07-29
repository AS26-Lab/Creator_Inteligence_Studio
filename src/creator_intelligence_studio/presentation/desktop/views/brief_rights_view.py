from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefRightsView(BriefSectionView):
    section_title = "Rights"
    data_method = "list_rights"
