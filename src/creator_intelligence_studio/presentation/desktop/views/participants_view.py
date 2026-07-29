from __future__ import annotations

from .production_base_view import ProductionSectionView


class ParticipantsView(ProductionSectionView):
    section_title = "Participants"
    data_method = "list_participants"
