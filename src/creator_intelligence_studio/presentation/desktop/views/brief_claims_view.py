from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefClaimsView(BriefSectionView):
    section_title = "Claims"
    data_method = "list_claims"
