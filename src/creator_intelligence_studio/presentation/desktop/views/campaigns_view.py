"""Vista de campañas estrategicas."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class CampaignsView(PlanningSectionView):
    section_title = "Campaigns"
    data_method = "list_campaigns"
