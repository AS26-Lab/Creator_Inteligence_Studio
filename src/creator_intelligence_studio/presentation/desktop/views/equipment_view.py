from __future__ import annotations

from .production_base_view import ProductionSectionView


class EquipmentView(ProductionSectionView):
    section_title = "Equipment"
    data_method = "list_equipment"
