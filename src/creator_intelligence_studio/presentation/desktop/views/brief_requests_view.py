from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefRequestsView(BriefSectionView):
    section_title = "Requests"
    data_method = "list_requests"
    scope = "creator"
