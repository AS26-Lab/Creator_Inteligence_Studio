from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefChecklistView(BriefSectionView):
    section_title = "Checklists"
    data_method = "list_checklists"
