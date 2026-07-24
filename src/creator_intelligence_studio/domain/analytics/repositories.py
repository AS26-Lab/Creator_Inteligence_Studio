"""Contratos de persistencia para analytics manual y aprendizaje."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    AnalyticsChannel,
    AnalyticsFieldMapping,
    AnalyticsImport,
    AnalyticsImportRow,
    AnalyticsMetricDefinition,
    AnalyticsMetricSnapshot,
    AnalyticsPlatform,
    AnalyticsPublication,
)


class AnalyticsRepository(ABC):
    @abstractmethod
    def upsert_platform(self, platform: AnalyticsPlatform) -> AnalyticsPlatform:
        raise NotImplementedError

    @abstractmethod
    def list_platforms(self) -> list[AnalyticsPlatform]:
        raise NotImplementedError

    @abstractmethod
    def get_platform_by_key(self, platform_key: str) -> AnalyticsPlatform | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_channel(self, channel: AnalyticsChannel) -> AnalyticsChannel:
        raise NotImplementedError

    @abstractmethod
    def list_channels(self, creator_id: str) -> list[AnalyticsChannel]:
        raise NotImplementedError

    @abstractmethod
    def get_channel_by_id(self, channel_id: str) -> AnalyticsChannel | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_publication(self, publication: AnalyticsPublication) -> AnalyticsPublication:
        raise NotImplementedError

    @abstractmethod
    def list_publications(self, creator_id: str, *, filters: dict[str, object] | None = None) -> list[AnalyticsPublication]:
        raise NotImplementedError

    @abstractmethod
    def get_publication_by_id(self, publication_id: str) -> AnalyticsPublication | None:
        raise NotImplementedError

    @abstractmethod
    def get_publication_by_dedupe_key(self, dedupe_key: str) -> AnalyticsPublication | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_metric_definition(self, metric_definition: AnalyticsMetricDefinition) -> AnalyticsMetricDefinition:
        raise NotImplementedError

    @abstractmethod
    def list_metric_definitions(self) -> list[AnalyticsMetricDefinition]:
        raise NotImplementedError

    @abstractmethod
    def get_metric_definition_by_key(self, metric_key: str) -> AnalyticsMetricDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_metric_snapshot(self, snapshot: AnalyticsMetricSnapshot) -> AnalyticsMetricSnapshot:
        raise NotImplementedError

    @abstractmethod
    def list_metric_snapshots(self, publication_id: str) -> list[AnalyticsMetricSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_metric_snapshots(self, publication_id: str) -> list[AnalyticsMetricSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def upsert_import(self, import_record: AnalyticsImport) -> AnalyticsImport:
        raise NotImplementedError

    @abstractmethod
    def get_import_by_id(self, import_id: str) -> AnalyticsImport | None:
        raise NotImplementedError

    @abstractmethod
    def list_imports(self, creator_id: str) -> list[AnalyticsImport]:
        raise NotImplementedError

    @abstractmethod
    def get_import_by_fingerprint(self, source_fingerprint: str) -> AnalyticsImport | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_import_row(self, row: AnalyticsImportRow) -> AnalyticsImportRow:
        raise NotImplementedError

    @abstractmethod
    def list_import_rows(self, import_id: str, *, status: str | None = None) -> list[AnalyticsImportRow]:
        raise NotImplementedError

    @abstractmethod
    def upsert_field_mapping(self, mapping: AnalyticsFieldMapping) -> AnalyticsFieldMapping:
        raise NotImplementedError

    @abstractmethod
    def list_field_mappings(self, *, creator_id: str | None = None, platform: str | None = None, active_only: bool = False) -> list[AnalyticsFieldMapping]:
        raise NotImplementedError

    @abstractmethod
    def get_field_mapping(self, mapping_id: str) -> AnalyticsFieldMapping | None:
        raise NotImplementedError
