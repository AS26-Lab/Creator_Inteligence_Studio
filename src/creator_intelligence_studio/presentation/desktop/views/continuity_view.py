from __future__ import annotations

from .production_base_view import ProductionSectionView


class ContinuityView(ProductionSectionView):
    section_title = "Continuity"
    data_method = "list_continuity"
