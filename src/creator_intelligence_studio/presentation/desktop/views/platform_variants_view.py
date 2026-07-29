from __future__ import annotations

from .production_base_view import ProductionSectionView


class PlatformVariantsView(ProductionSectionView):
    section_title = "Platform Variants"
    data_method = "list_variants"
