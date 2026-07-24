"""Servicio de comparacion para Analytics Lab."""

from __future__ import annotations

from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService


class AnalyticsComparisonService:
    def __init__(self, lab_service: AnalyticsLabService) -> None:
        self.lab_service = lab_service

    def compare_publication(self, publication_id: str, cohort_id: str):
        return self.lab_service.compare_publication(publication_id, cohort_id)

    def get_analysis(self, run_id: str):
        return self.lab_service.get_analysis_detail(run_id)

    def get_analysis_run(self, run_id: str):
        return self.lab_service.get_analysis_run(run_id)

