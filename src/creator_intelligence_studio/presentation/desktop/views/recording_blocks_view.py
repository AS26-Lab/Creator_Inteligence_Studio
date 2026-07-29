from __future__ import annotations

from .production_base_view import ProductionSectionView


class RecordingBlocksView(ProductionSectionView):
    section_title = "Recording Blocks"
    data_method = "list_recording_blocks"
