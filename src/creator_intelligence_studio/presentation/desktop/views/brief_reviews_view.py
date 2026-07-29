from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefReviewsView(BriefSectionView):
    section_title = "Reviews"
    data_method = "list_reviews"
