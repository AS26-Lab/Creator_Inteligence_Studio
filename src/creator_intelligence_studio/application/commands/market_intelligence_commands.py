"""Comandos de aplicacion para Market and Trend Intelligence Foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListMarketDefinitionsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateMarketDefinitionCommand:
    creator_id: str
    name: str
    description: str | None = None
    market_type: str = "market"
    primary_language: str | None = None
    primary_region: str | None = None


@dataclass(frozen=True, slots=True)
class CreateMarketTopicCommand:
    creator_id: str
    market_id: str
    canonical_name: str
    display_name: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterMarketSourceCommand:
    creator_id: str
    source_type: str
    name: str
    access_method: str
    trust_level: str
    permission_status: str = "unknown"
    enabled: bool = True
    platform: str | None = None
    source_identifier: str | None = None
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class CreateResearchQueryCommand:
    creator_id: str
    platform: str
    query_text: str | None = None
    query_type: str = "search"
    market_id: str | None = None
    language: str | None = None
    region: str | None = None
    published_after: str | None = None
    published_before: str | None = None
    max_results: int = 25


@dataclass(frozen=True, slots=True)
class RunResearchQueryCommand:
    query_id: str


@dataclass(frozen=True, slots=True)
class ListMarketSignalsCommand:
    creator_id: str
    market_id: str | None = None


@dataclass(frozen=True, slots=True)
class BuildMarketReportCommand:
    creator_id: str
    market_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExportMarketReportCommand:
    report_id: str
    format: str

