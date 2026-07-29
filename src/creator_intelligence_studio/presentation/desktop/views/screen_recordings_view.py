from __future__ import annotations

from .production_base_view import ProductionSectionView


class ScreenRecordingsView(ProductionSectionView):
    section_title = "Screen Recordings"
    data_method = "list_screen_recordings"
