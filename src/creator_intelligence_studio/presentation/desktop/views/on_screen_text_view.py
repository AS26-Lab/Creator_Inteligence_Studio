from __future__ import annotations

from .production_base_view import ProductionSectionView


class OnScreenTextView(ProductionSectionView):
    section_title = "On-Screen Text"
    data_method = "list_on_screen_text"
