"""Comandos de alto nivel para Script Outline and Production Preparation Foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateProductionRequestCommand:
    creator_id: str
    brief_id: str
    request_type: str | None = None


@dataclass(frozen=True, slots=True)
class GenerateOutlineCommand:
    request_id: str | None = None
    creator_id: str | None = None
    brief_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewOutlineCommand:
    outline_id: str
    decision: str
    reason: str


@dataclass(frozen=True, slots=True)
class VersionOutlineCommand:
    outline_id: str
    reason: str = "versioned_outline"
