from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefRisksView(BriefSectionView):
    section_title = "Risks"
    data_method = "list_risks"
