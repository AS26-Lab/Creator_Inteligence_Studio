from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefPlatformAdaptationsView(BriefSectionView):
    section_title = "Platform Adaptations"
    data_method = "list_adaptations"
