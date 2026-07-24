"""Comandos de aplicacion para analytics manual y aprendizaje."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ListAnalyticsPlatformsCommand:
    pass


@dataclass(frozen=True, slots=True)
class ListAnalyticsChannelsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateAnalyticsChannelCommand:
    creator_id: str
    platform: str
    name: str
    external_channel_id: str | None = None
    channel_url: str | None = None
    timezone_name: str | None = None
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class ListAnalyticsImportsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ImportAnalyticsCsvCommand:
    creator_id: str
    file: Path
    channel_id: str | None = None
    platform: str | None = None
    mapping_name: str | None = None
    delimiter: str | None = None


@dataclass(frozen=True, slots=True)
class ImportAnalyticsExcelCommand:
    creator_id: str
    file: Path
    channel_id: str | None = None
    platform: str | None = None
    sheet_name: str | None = None
    mapping_name: str | None = None


@dataclass(frozen=True, slots=True)
class InspectAnalyticsFileCommand:
    file: Path
    sheet_name: str | None = None


@dataclass(frozen=True, slots=True)
class DetectAnalyticsSchemaCommand:
    file: Path
    sheet_name: str | None = None


@dataclass(frozen=True, slots=True)
class ListAnalyticsMappingsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class SaveAnalyticsMappingCommand:
    creator_id: str | None
    platform: str
    mapping_name: str
    source_field: str
    target_field: str
    transformation: str = "identity"
    confidence: float = 1.0
    active: bool = True


@dataclass(frozen=True, slots=True)
class ListAnalyticsPublicationsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowAnalyticsPublicationCommand:
    publication_id: str


@dataclass(frozen=True, slots=True)
class PublicationMetricsCommand:
    publication_id: str


@dataclass(frozen=True, slots=True)
class ShowAnalyticsImportCommand:
    import_id: str


@dataclass(frozen=True, slots=True)
class ListAnalyticsImportRowsCommand:
    import_id: str


@dataclass(frozen=True, slots=True)
class ExportNormalizedAnalyticsCommand:
    creator_id: str
    format: str
