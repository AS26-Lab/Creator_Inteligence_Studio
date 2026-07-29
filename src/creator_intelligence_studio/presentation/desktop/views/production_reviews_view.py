from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionReviewsView(ProductionSectionView):
    section_title = "Reviews"
    data_method = "list_reviews"
