from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionOverviewView(ProductionSectionView):
    section_title = "Production Preparation"
    data_method = "list_outlines"
    scope = "creator"

    def refresh(self) -> None:
        production_service = getattr(self.workspace, "production_service", None)
        creator_id = self._creator_id()
        if production_service is not None and creator_id is not None:
            overview = production_service.build_overview(creator_id)
            self.subtitle.setText(
                f"Outlines: {overview.get('total_outlines', 0)} | "
                f"Needs review: {overview.get('needs_review', 0)} | "
                f"Blocked: {overview.get('blocked', 0)} | "
                f"Ready recording: {overview.get('ready_for_recording', 0)}"
            )
        super().refresh()
