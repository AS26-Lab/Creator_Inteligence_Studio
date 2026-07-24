"""Servicio de findings para Analytics Lab."""

from __future__ import annotations

from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService


class AnalyticsFindingService:
    def __init__(self, lab_service: AnalyticsLabService) -> None:
        self.lab_service = lab_service

    def list_findings(self, creator_id: str, *, filters: dict[str, object] | None = None):
        return self.lab_service.list_findings(creator_id, filters=filters)

    def get_finding(self, finding_id: str):
        return self.lab_service.get_finding(finding_id)

    def confirm_finding(self, finding_id: str):
        return self.lab_service.confirm_finding(finding_id)

    def reject_finding(self, finding_id: str):
        return self.lab_service.reject_finding(finding_id)

