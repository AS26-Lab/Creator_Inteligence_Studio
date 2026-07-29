from __future__ import annotations

from .production_base_view import ProductionSectionView


class ScriptOutlinesView(ProductionSectionView):
    section_title = "Script Outlines"
    data_method = "list_outlines"
    scope = "creator"
