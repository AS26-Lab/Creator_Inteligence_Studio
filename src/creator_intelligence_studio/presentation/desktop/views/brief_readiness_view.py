from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefReadinessView(BriefSectionView):
    section_title = "Readiness"
    data_method = "list_gates"
