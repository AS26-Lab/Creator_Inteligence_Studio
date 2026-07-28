"""Tipos de explicacion."""

from __future__ import annotations

from enum import Enum


class ExplanationType(str, Enum):
    SUMMARY = "summary"
    EVIDENCE = "evidence"
    RISK = "risk"
    CONSTRAINT = "constraint"
    ALTERNATIVE = "alternative"
