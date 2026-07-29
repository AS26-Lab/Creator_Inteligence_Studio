from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefsOverviewView(BriefSectionView):
    section_title = "Content Briefs"
    data_method = "list_briefs"
    scope = "creator"

    def refresh(self) -> None:
        brief_service = getattr(self.workspace, "brief_service", None)
        creator_id = self._creator_id()
        if brief_service is not None and creator_id is not None:
            overview = brief_service.build_overview(creator_id)
            self.subtitle.setText(
                f"Briefs: {overview.get('total_briefs', 0)} | "
                f"Needs review: {overview.get('needs_review', 0)} | "
                f"Blocked: {overview.get('blocked', 0)} | "
                f"Ready preproduction: {overview.get('ready_for_preproduction', 0)}"
            )
        super().refresh()
