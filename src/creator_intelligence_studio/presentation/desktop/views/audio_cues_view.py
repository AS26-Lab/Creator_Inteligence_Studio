from __future__ import annotations

from .production_base_view import ProductionSectionView


class AudioCuesView(ProductionSectionView):
    section_title = "Audio Cues"
    data_method = "list_audio_cues"
