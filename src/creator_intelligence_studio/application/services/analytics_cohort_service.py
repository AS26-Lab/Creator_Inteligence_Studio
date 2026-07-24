"""Servicio de cohortes para Analytics Lab."""

from __future__ import annotations

from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService


class AnalyticsCohortService:
    def __init__(self, lab_service: AnalyticsLabService) -> None:
        self.lab_service = lab_service

    def list_cohorts(self, creator_id: str):
        return self.lab_service.list_cohorts(creator_id)

    def create_cohort(self, **kwargs):
        return self.lab_service.create_cohort(**kwargs)

    def update_cohort(self, cohort_id: str, **changes):
        return self.lab_service.update_cohort(cohort_id, **changes)

    def archive_cohort(self, cohort_id: str):
        return self.lab_service.archive_cohort(cohort_id)

    def get_cohort(self, cohort_id: str):
        return self.lab_service.get_cohort(cohort_id)

    def analyze_cohort(self, cohort_id: str):
        return self.lab_service.analyze_cohort(cohort_id)

