"""Servicio de reportes para Analytics Lab."""

from __future__ import annotations

from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService


class AnalyticsReportService:
    def __init__(self, lab_service: AnalyticsLabService) -> None:
        self.lab_service = lab_service

    def generate_weekly_report(self, *, creator_id: str, period_start: str, period_end: str):
        return self.lab_service.generate_weekly_report(creator_id=creator_id, period_start=period_start, period_end=period_end)

    def list_reports(self, creator_id: str):
        return self.lab_service.list_reports(creator_id)

    def get_report(self, report_id: str):
        return self.lab_service.get_report(report_id)

    def get_report_detail(self, report_id: str):
        return self.lab_service.get_report_detail(report_id)

    def export_report(self, report_id: str, format_name: str):
        return self.lab_service.export_report(report_id, format_name)

