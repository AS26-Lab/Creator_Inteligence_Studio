"""Comandos de Creator Language Analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateCreatorLanguageCorpusCommand:
    creator_id: str
    name: str


@dataclass(frozen=True, slots=True)
class ListCreatorLanguageCorporaCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowCreatorLanguageCorpusCommand:
    corpus_id: str


@dataclass(frozen=True, slots=True)
class AddCreatorLanguageCorpusSourceCommand:
    corpus_id: str
    source_type: str
    source_id: str


@dataclass(frozen=True, slots=True)
class RemoveCreatorLanguageCorpusSourceCommand:
    source_id: str


@dataclass(frozen=True, slots=True)
class AnalyzeCreatorLanguageCorpusCommand:
    corpus_id: str


@dataclass(frozen=True, slots=True)
class ShowCreatorLanguageAnalysisCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListCreatorLanguagePatternsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowCreatorLanguagePatternCommand:
    pattern_id: str


@dataclass(frozen=True, slots=True)
class ShowCreatorLanguageProfileCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CompareCreatorLanguageProfilesCommand:
    creator_id: str
    base_profile_version: int
    compare_profile_version: int


@dataclass(frozen=True, slots=True)
class ListCreatorLanguageCandidatesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ReviewCreatorLanguageCandidateCommand:
    candidate_id: str
    decision: str


@dataclass(frozen=True, slots=True)
class RetrieveCreatorLanguageCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ExportCreatorLanguageCommand:
    creator_id: str
    format: str
