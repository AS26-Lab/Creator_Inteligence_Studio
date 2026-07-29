from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefShotPlanView(BriefSectionView):
    section_title = "Shot Plan"
    data_method = "list_shots"
