from __future__ import annotations

from .production_base_view import ProductionSectionView


class LocationsView(ProductionSectionView):
    section_title = "Locations"
    data_method = "list_locations"
