"""Facade de reportes unificados."""

from __future__ import annotations

from pathlib import Path

from .platform_integration_service import PlatformIntegrationService


class PlatformReportService(PlatformIntegrationService):
    def export_report(self, report_id: str, format_name: str = "json", *, destination: Path | None = None):
        return super().export_report(report_id, format_name, destination=destination)
