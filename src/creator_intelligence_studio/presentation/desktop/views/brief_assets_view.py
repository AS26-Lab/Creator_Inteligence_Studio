from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefAssetsView(BriefSectionView):
    section_title = "Assets"
    data_method = "list_assets"
