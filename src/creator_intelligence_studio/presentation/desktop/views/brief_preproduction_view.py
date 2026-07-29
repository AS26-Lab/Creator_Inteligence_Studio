from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefPreproductionView(BriefSectionView):
    section_title = "Pre-Production"
    data_method = "list_requirements"
