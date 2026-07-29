from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefHistoryView(BriefSectionView):
    section_title = "History"
    data_method = "list_snapshots"
