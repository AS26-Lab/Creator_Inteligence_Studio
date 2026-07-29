from __future__ import annotations

from .production_base_view import ProductionSectionView


class RecordingOrderView(ProductionSectionView):
    section_title = "Recording Order"
    data_method = "list_recording_block_items"
