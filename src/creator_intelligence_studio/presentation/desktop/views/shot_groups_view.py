from __future__ import annotations

from .production_base_view import ProductionSectionView


class ShotGroupsView(ProductionSectionView):
    section_title = "Shot Groups"
    data_method = "list_shot_groups"
