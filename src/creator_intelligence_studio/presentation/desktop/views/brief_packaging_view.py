from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefPackagingView(BriefSectionView):
    section_title = "Packaging"
    data_method = "list_packaging"
