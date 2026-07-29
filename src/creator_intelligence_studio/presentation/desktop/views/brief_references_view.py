from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefReferencesView(BriefSectionView):
    section_title = "References"
    data_method = "list_references"
