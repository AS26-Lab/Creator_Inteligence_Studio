from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefApprovalGatesView(BriefSectionView):
    section_title = "Approval Gates"
    data_method = "list_gates"
