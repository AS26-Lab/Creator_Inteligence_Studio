from __future__ import annotations

from .production_base_view import ProductionSectionView


class ClaimsProofView(ProductionSectionView):
    section_title = "Claims & Proof"
    data_method = "list_claim_links"
