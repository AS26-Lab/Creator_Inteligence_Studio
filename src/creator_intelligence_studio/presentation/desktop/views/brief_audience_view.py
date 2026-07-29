from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefAudienceView(BriefSectionView):
    section_title = "Audience"
    data_method = "list_audience_definitions"
