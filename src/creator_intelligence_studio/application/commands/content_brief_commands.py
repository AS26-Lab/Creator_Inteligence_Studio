"""Comandos de alto nivel para Content Brief and Pre-Production Foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateBriefRequestCommand:
    creator_id: str
    source_type: str
    source_id: str | None
    request_type: str | None = None


@dataclass(frozen=True, slots=True)
class GenerateBriefCommand:
    request_id: str | None = None
    creator_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewBriefCommand:
    brief_id: str
    decision: str
    reason: str


@dataclass(frozen=True, slots=True)
class VersionBriefCommand:
    brief_id: str
    reason: str = "versioned_brief"

