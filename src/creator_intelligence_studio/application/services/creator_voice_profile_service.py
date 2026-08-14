"""Deterministic Creator Voice profile synthesis from evidence snapshots."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from statistics import median
from typing import Any

from creator_intelligence_studio.domain.creator_corpus import CorpusAuthorshipClass
from creator_intelligence_studio.domain.creator_voice import (
    CreatorVoiceConfidenceLevel,
    CreatorVoiceEvidenceItem,
    CreatorVoiceEvidenceSnapshot,
    CreatorVoiceEvidenceType,
    CreatorVoiceFeature,
    CreatorVoiceFeatureStatus,
    CreatorVoiceProfile,
    CreatorVoiceProfileComparison,
    CreatorVoiceProfileSection,
    CreatorVoiceProfileStatus,
    CreatorVoiceProfileVersion,
    CreatorVoiceScopeMode,
    CreatorVoiceStructuredPreference,
)
from creator_intelligence_studio.infrastructure.creator_language.filler_word_analyzer import analyze_filler_words
from creator_intelligence_studio.infrastructure.creator_language.phrase_frequency_analyzer import analyze_phrase_frequency
from creator_intelligence_studio.infrastructure.creator_language.sentence_style_analyzer import analyze_sentence_style
from creator_intelligence_studio.infrastructure.creator_language.tokenizer import normalize_language_text, tokenize_language_text
from creator_intelligence_studio.shared.dates import utc_now


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _stable_id(*parts: object) -> str:
    return _hash_text(_stable_json(parts))


def _normalize_text(value: str | None) -> str:
    return normalize_language_text(value)


def _word_count(value: str | None) -> int:
    clean = _normalize_text(value)
    if not clean:
        return 0
    return len(clean.split())


def _paragraph_count(value: str | None) -> int:
    clean = _normalize_text(value)
    if not clean:
        return 0
    paragraphs = [item for item in re.split(r"\n{2,}", clean) if item.strip()]
    return max(1, len(paragraphs))


def _is_sensitive_token(token: str) -> bool:
    lowered = token.casefold()
    if not lowered:
        return True
    if "@" in lowered or "http://" in lowered or "https://" in lowered or lowered.startswith("www."):
        return True
    if re.fullmatch(r"\+?\d[\d\-\s()]{6,}", lowered):
        return True
    if re.fullmatch(r"[a-z0-9]{12,}", lowered) and any(char.isdigit() for char in lowered):
        return True
    if re.fullmatch(r"[a-f0-9]{16,}", lowered):
        return True
    return False


def _safe_phrase(phrase: str) -> str | None:
    normalized = _normalize_text(phrase).casefold()
    if not normalized:
        return None
    tokens = [token.normalized for token in tokenize_language_text(normalized).tokens if token.normalized.strip()]
    if not tokens:
        return None
    if any(_is_sensitive_token(token) for token in tokens):
        return None
    if len(tokens) > 4:
        return None
    return " ".join(tokens)


def _weighted_average(pairs: list[tuple[float, float]]) -> float | None:
    total_weight = sum(weight for _, weight in pairs)
    if not total_weight:
        return None
    return sum(value * weight for value, weight in pairs) / total_weight


def _weighted_median(pairs: list[tuple[float, float]]) -> float | None:
    filtered = [(value, weight) for value, weight in pairs if weight > 0]
    if not filtered:
        return None
    ordered = sorted(filtered, key=lambda item: item[0])
    threshold = sum(weight for _, weight in ordered) / 2.0
    running = 0.0
    for value, weight in ordered:
        running += weight
        if running >= threshold:
            return value
    return ordered[-1][0]


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _confidence_from_support(
    *,
    evidence_words: float,
    item_count: int,
    source_count: int,
    consistency: float,
) -> CreatorVoiceConfidenceLevel:
    if evidence_words < 120 or item_count < 2 or source_count < 2:
        return CreatorVoiceConfidenceLevel.LOW
    if evidence_words >= 300 and item_count >= 3 and source_count >= 3 and consistency >= 0.6:
        return CreatorVoiceConfidenceLevel.HIGH
    return CreatorVoiceConfidenceLevel.MEDIUM


def _feature_status(
    *,
    evidence_words: float,
    item_count: int,
    source_count: int,
    confidence: CreatorVoiceConfidenceLevel,
) -> CreatorVoiceFeatureStatus:
    if evidence_words < 80 or item_count < 2 or source_count < 2:
        return CreatorVoiceFeatureStatus.INSUFFICIENT_EVIDENCE
    if confidence == CreatorVoiceConfidenceLevel.HIGH and evidence_words >= 180 and source_count >= 3:
        return CreatorVoiceFeatureStatus.READY
    return CreatorVoiceFeatureStatus.PARTIAL


def _profile_status(*, evidence_words: float, source_count: int) -> CreatorVoiceProfileStatus:
    if evidence_words < 120 or source_count < 2:
        return CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE
    if evidence_words >= 200 and source_count >= 3:
        return CreatorVoiceProfileStatus.READY
    return CreatorVoiceProfileStatus.PARTIAL


def _profile_confidence(*, status: CreatorVoiceProfileStatus, section_confidence_values: list[CreatorVoiceConfidenceLevel], warnings: tuple[str, ...]) -> CreatorVoiceConfidenceLevel:
    if status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
        return CreatorVoiceConfidenceLevel.LOW
    if status == CreatorVoiceProfileStatus.PARTIAL:
        return CreatorVoiceConfidenceLevel.MEDIUM
    if warnings:
        return CreatorVoiceConfidenceLevel.MEDIUM
    if section_confidence_values.count(CreatorVoiceConfidenceLevel.HIGH) >= max(1, len(section_confidence_values) - 1):
        return CreatorVoiceConfidenceLevel.HIGH
    return CreatorVoiceConfidenceLevel.MEDIUM


def _confidence_rank(value: CreatorVoiceConfidenceLevel) -> int:
    return {
        CreatorVoiceConfidenceLevel.LOW: 0,
        CreatorVoiceConfidenceLevel.MEDIUM: 1,
        CreatorVoiceConfidenceLevel.HIGH: 2,
    }[value]


def _language_key(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    return normalized.casefold() if normalized else None


@dataclass(frozen=True, slots=True)
class _ItemAnalysis:
    item: CreatorVoiceEvidenceItem
    weight: float
    word_count: int
    paragraph_count: int
    sentence_lengths: tuple[int, ...]
    total_tokens: int
    unique_tokens: int
    first_person_count: int
    second_person_count: int
    question_count: int
    exclamation_count: int
    ellipsis_count: int
    list_count: int
    filler_rate: float
    repeated_phrases: tuple[tuple[str, int], ...]


class CreatorVoiceProfileService:
    PROFILE_VERSION = CreatorVoiceProfileVersion.V1
    FEATURE_ALGORITHM_VERSION = "creator-voice-profile-feature-v1"

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_voice_profile")

    def _analyze_item(self, item: CreatorVoiceEvidenceItem) -> _ItemAnalysis | None:
        if item.evidence_type == CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE:
            return None
        text = _normalize_text(item.text_reference)
        if not text:
            return None
        sentence_style = analyze_sentence_style(text)
        filler = analyze_filler_words(text)
        phrase_frequency = analyze_phrase_frequency(text)
        tokens = [token.normalized for token in tokenize_language_text(text).tokens if token.normalized.strip()]
        return _ItemAnalysis(
            item=item,
            weight=max(0.05, float(item.evidence_weight or 0.0)),
            word_count=_word_count(text),
            paragraph_count=_paragraph_count(text),
            sentence_lengths=tuple(int(length) for length in sentence_style["sentence_length_distribution"] if int(length) > 0),
            total_tokens=int(sentence_style["total_tokens"]),
            unique_tokens=int(sentence_style["unique_tokens"]),
            first_person_count=max(0, int(round(float(sentence_style["first_person_ratio"]) * max(1, int(sentence_style["total_tokens"])) ))),
            second_person_count=max(0, int(round(float(sentence_style["second_person_ratio"]) * max(1, int(sentence_style["total_tokens"])) ))),
            question_count=max(0, int(round(float(sentence_style["question_ratio"]) * max(1, len(sentence_style["sentence_length_distribution"]))))),
            exclamation_count=max(0, int(round(float(sentence_style["exclamation_ratio"]) * max(1, len(sentence_style["sentence_length_distribution"]))))),
            ellipsis_count=text.count("...") + text.count("…"),
            list_count=sum(1 for line in text.splitlines() if line.strip().startswith(("-", "*", "•", "1.", "2.", "3."))),
            filler_rate=float(filler["rate"]),
            repeated_phrases=tuple(
                (safe_phrase, int(count))
                for raw_phrase, count in (
                    phrase_frequency["top_bigrams"][:5] + phrase_frequency["top_trigrams"][:5]
                )
                if (safe_phrase := _safe_phrase(raw_phrase)) is not None and int(count) > 1
            ),
        )

    def _profile_items(self, snapshot: CreatorVoiceEvidenceSnapshot) -> list[CreatorVoiceEvidenceItem]:
        spoken_sources_with_segments = {
            (item.document_id, item.version_id)
            for item in snapshot.evidence_items
            if item.evidence_type == CreatorVoiceEvidenceType.CREATOR_SPOKEN and item.segment_id is not None
        }
        filtered: list[CreatorVoiceEvidenceItem] = []
        for item in snapshot.evidence_items:
            if item.evidence_type == CreatorVoiceEvidenceType.CREATOR_SPOKEN and item.segment_id is None:
                if (item.document_id, item.version_id) in spoken_sources_with_segments:
                    continue
            filtered.append(item)
        return filtered

    def _confidence_for_values(self, items: list[_ItemAnalysis], values: list[tuple[float, float]]) -> CreatorVoiceConfidenceLevel:
        if not items:
            return CreatorVoiceConfidenceLevel.LOW
        median_value = _weighted_median(values)
        if median_value is None:
            return CreatorVoiceConfidenceLevel.LOW
        spread = [abs(value - median_value) for value, _ in values]
        average_spread = sum(spread) / max(1, len(spread))
        consistency = max(0.0, 1.0 - (average_spread / max(1.0, median_value)))
        evidence_words = sum(item.word_count * item.weight for item in items)
        source_count = len({item.item.source_identity for item in items})
        return _confidence_from_support(
            evidence_words=evidence_words,
            item_count=len(items),
            source_count=source_count,
            consistency=consistency,
        )

    def _feature_basis(self, items: list[_ItemAnalysis]) -> dict[str, object]:
        source_ids = []
        seen_sources: set[str] = set()
        for item in items:
            if item.item.source_identity not in seen_sources:
                seen_sources.add(item.item.source_identity)
                source_ids.append(item.item.source_identity)
        type_counts = Counter(item.item.evidence_type.value for item in items)
        quality_counts = Counter(item.item.evidence_quality.value for item in items)
        authorship_counts = Counter(item.item.authorship_class.value for item in items if item.item.authorship_class is not None)
        return {
            "item_count": len(items),
            "source_count": len(seen_sources),
            "supporting_item_ids": [item.item.id for item in items[:5]],
            "supporting_source_ids": source_ids[:5],
            "evidence_type_counts": dict(type_counts),
            "quality_counts": dict(quality_counts),
            "authorship_counts": dict(authorship_counts),
            "weighted_word_count": round(sum(item.word_count * item.weight for item in items), 3),
        }

    def _build_numeric_feature(
        self,
        *,
        feature_key: str,
        section_key: str,
        title: str,
        items: list[_ItemAnalysis],
        values: list[tuple[float, float]],
        unit: str,
    ) -> CreatorVoiceFeature:
        weighted_values = [pair for pair in values if pair[0] >= 0]
        median_value = _weighted_median(weighted_values)
        weighted_average = _weighted_average(weighted_values)
        value = {
            "median": median_value,
            "average": weighted_average,
        }
        evidence_words = sum(item.word_count * item.weight for item in items)
        source_count = len({item.item.source_identity for item in items})
        confidence = self._confidence_for_values(items, weighted_values)
        status = _feature_status(
            evidence_words=evidence_words,
            item_count=len(items),
            source_count=source_count,
            confidence=confidence,
        )
        return CreatorVoiceFeature(
            id=_stable_id(feature_key, section_key, title, value, unit, self._feature_basis(items)),
            feature_key=feature_key,
            section_key=section_key,
            title=title,
            value=value,
            unit=unit,
            status=status,
            confidence=confidence,
            evidence_item_count=len(items),
            independent_source_count=source_count,
            weighted_evidence_count=round(evidence_words, 3),
            evidence_weight_sum=round(sum(item.weight for item in items), 3),
            evidence_basis=self._feature_basis(items),
        )

    def _build_ratio_feature(
        self,
        *,
        feature_key: str,
        section_key: str,
        title: str,
        items: list[_ItemAnalysis],
        numerator: float,
        denominator: float,
        unit: str,
        extra_values: dict[str, object] | None = None,
    ) -> CreatorVoiceFeature:
        evidence_words = sum(item.word_count * item.weight for item in items)
        source_count = len({item.item.source_identity for item in items})
        confidence = _confidence_from_support(
            evidence_words=evidence_words,
            item_count=len(items),
            source_count=source_count,
            consistency=0.65,
        )
        status = _feature_status(
            evidence_words=evidence_words,
            item_count=len(items),
            source_count=source_count,
            confidence=confidence,
        )
        value = {"ratio": _ratio(numerator, denominator)}
        if extra_values:
            value.update(extra_values)
        return CreatorVoiceFeature(
            id=_stable_id(feature_key, section_key, title, value, unit, self._feature_basis(items)),
            feature_key=feature_key,
            section_key=section_key,
            title=title,
            value=value,
            unit=unit,
            status=status,
            confidence=confidence,
            evidence_item_count=len(items),
            independent_source_count=source_count,
            weighted_evidence_count=round(evidence_words, 3),
            evidence_weight_sum=round(sum(item.weight for item in items), 3),
            evidence_basis=self._feature_basis(items),
        )

    def _build_repeated_phrase_feature(
        self,
        *,
        section_key: str,
        items: list[_ItemAnalysis],
    ) -> CreatorVoiceFeature:
        phrase_counts: dict[str, float] = defaultdict(float)
        phrase_sources: dict[str, set[str]] = defaultdict(set)
        for item in items:
            for phrase, count in item.repeated_phrases:
                if not phrase:
                    continue
                phrase_counts[phrase] += count * item.weight
                phrase_sources[phrase].add(item.item.source_identity)
        repeated = [
            {
                "phrase": phrase,
                "weighted_count": round(count, 3),
                "source_count": len(phrase_sources[phrase]),
            }
            for phrase, count in sorted(phrase_counts.items(), key=lambda pair: (-pair[1], pair[0]))
            if len(phrase_sources[phrase]) >= 2 and count >= 2
        ][:5]
        evidence_words = sum(item.word_count * item.weight for item in items)
        source_count = len({item.item.source_identity for item in items})
        confidence = _confidence_from_support(
            evidence_words=evidence_words,
            item_count=len(items),
            source_count=source_count,
            consistency=0.55,
        )
        status = _feature_status(
            evidence_words=evidence_words,
            item_count=len(items),
            source_count=source_count,
            confidence=confidence,
        )
        return CreatorVoiceFeature(
            id=_stable_id("repeated_phrases", section_key, repeated, self._feature_basis(items)),
            feature_key="repeated_phrases",
            section_key=section_key,
            title="Repeated phrases",
            value=repeated,
            unit="phrase",
            status=status,
            confidence=confidence,
            evidence_item_count=len(items),
            independent_source_count=source_count,
            weighted_evidence_count=round(evidence_words, 3),
            evidence_weight_sum=round(sum(item.weight for item in items), 3),
            evidence_basis=self._feature_basis(items),
            warnings=() if repeated else ("too_little_signal",),
        )

    def _render_preference_text(self, value: dict[str, object], scope: CreatorVoiceScopeMode) -> str:
        scope_label = {
            CreatorVoiceScopeMode.CREATOR_GLOBAL: "para todos tus proyectos",
            CreatorVoiceScopeMode.PROJECT_SPECIFIC: "solo para este proyecto",
            CreatorVoiceScopeMode.WORKFLOW_SPECIFIC: "solo para este flujo de trabajo",
        }[scope]
        direction = str(value.get("direction") or "").strip().lower()
        preference_type = str(value.get("preference_type") or "content_length_preference")
        if preference_type == "content_length_preference":
            if direction == "shorter":
                return f"{scope_label}: preferir introducciones mas breves."
            if direction == "longer":
                return f"{scope_label}: preferir introducciones mas detalladas."
        return f"{scope_label}: preferencia confirmada."

    def _preference_direction(self, text_reference: str | None) -> str | None:
        normalized = _normalize_text(text_reference).casefold()
        if not normalized:
            return None
        shorter_tokens = ("mas breves", "introducciones mas breves", "shorter")
        longer_tokens = ("mas detalladas", "introducciones mas detalladas", "longer")
        if any(token in normalized for token in shorter_tokens):
            return "shorter"
        if any(token in normalized for token in longer_tokens):
            return "longer"
        return None

    def _build_structured_preferences(self, snapshot: CreatorVoiceEvidenceSnapshot, text_items: list[_ItemAnalysis]) -> tuple[CreatorVoiceStructuredPreference, ...]:
        preferences: list[CreatorVoiceStructuredPreference] = []
        length_feature = next((item for item in self._all_features(text_items) if item.feature_key == "typical_word_count"), None)
        observed_length = float(length_feature.value["median"]) if length_feature and isinstance(length_feature.value, dict) else None
        for item in snapshot.evidence_items:
            if item.evidence_type != CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE:
                continue
            direction = self._preference_direction(item.text_reference)
            value = {
                "preference_type": "content_length_preference",
                "direction": direction,
                "source": "confirmed_preference",
            }
            observed_pattern = None
            conflict = False
            warning = None
            if direction == "shorter":
                observed_pattern = "observed_longer_texts" if observed_length is not None else None
                conflict = bool(observed_length is not None and observed_length >= 18)
            elif direction == "longer":
                observed_pattern = "observed_shorter_texts" if observed_length is not None else None
                conflict = bool(observed_length is not None and observed_length <= 14)
            if conflict:
                warning = "observed_text_pattern_conflicts_with_confirmed_preference"
            preferences.append(
                CreatorVoiceStructuredPreference(
                    id=item.id,
                    preference_key=item.source_identity,
                    preference_type="content_length_preference",
                    scope=item.source_scope,
                    project_id=item.project_id,
                    workflow_type=item.workflow_type,
                    value=value,
                    rendered_text=_normalize_text(item.text_reference),
                    observed_pattern=observed_pattern,
                    conflict=conflict,
                    warning=warning,
                    evidence_basis={
                        "evidence_item_id": item.id,
                        "source_identity": item.source_identity,
                        "evidence_weight": item.evidence_weight,
                        "quality": item.evidence_quality.value,
                    },
                    confirmed_at=item.created_at,
                )
            )
        return tuple(preferences)

    def _all_features(self, text_items: list[_ItemAnalysis]) -> tuple[CreatorVoiceFeature, ...]:
        if not text_items:
            return ()
        written_items = [item for item in text_items if item.item.evidence_type in {CreatorVoiceEvidenceType.CREATOR_WRITTEN, CreatorVoiceEvidenceType.CREATOR_EDITED}]
        spoken_items = [item for item in text_items if item.item.evidence_type == CreatorVoiceEvidenceType.CREATOR_SPOKEN]

        all_sentence_lengths = [(length, item.weight) for item in text_items for length in item.sentence_lengths]
        all_items = text_items
        total_weighted_words = sum(item.word_count * item.weight for item in all_items)
        total_paragraphs = sum(item.paragraph_count * item.weight for item in all_items)
        total_sentences = sum(len(item.sentence_lengths) * item.weight for item in all_items)
        total_first_person = sum(item.first_person_count * item.weight for item in all_items)
        total_second_person = sum(item.second_person_count * item.weight for item in all_items)
        total_questions = sum(item.question_count * item.weight for item in all_items)
        total_exclamations = sum(item.exclamation_count * item.weight for item in all_items)
        total_ellipsis = sum(item.ellipsis_count * item.weight for item in all_items)
        total_lists = sum(item.list_count * item.weight for item in all_items)
        total_tokens = sum(item.total_tokens * item.weight for item in all_items)
        unique_tokens = sum(item.unique_tokens * item.weight for item in all_items)
        repeated_tokens = sum(max(0, item.total_tokens - item.unique_tokens) * item.weight for item in all_items)
        spoken_filler_weight = sum(item.filler_rate * item.weight for item in spoken_items)
        spoken_word_weight = sum(item.word_count * item.weight for item in spoken_items)

        features = [
            self._build_numeric_feature(
                feature_key="typical_word_count",
                section_key="length",
                title="Typical word count",
                items=all_items,
                values=[(float(item.word_count), item.weight) for item in all_items],
                unit="words",
            ),
            self._build_numeric_feature(
                feature_key="typical_paragraph_count",
                section_key="length",
                title="Typical paragraph count",
                items=all_items,
                values=[(float(item.paragraph_count), item.weight) for item in all_items],
                unit="paragraphs",
            ),
            self._build_numeric_feature(
                feature_key="median_sentence_length",
                section_key="sentence_structure",
                title="Median sentence length",
                items=all_items,
                values=[(float(length), weight) for length, weight in all_sentence_lengths],
                unit="words",
            ),
            self._build_ratio_feature(
                feature_key="short_sentence_ratio",
                section_key="sentence_structure",
                title="Short sentence ratio",
                items=all_items,
                numerator=sum(1.0 for item in all_items for length in item.sentence_lengths if length <= 8),
                denominator=sum(len(item.sentence_lengths) for item in all_items),
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="paragraph_density",
                section_key="formatting",
                title="Paragraph density",
                items=all_items,
                numerator=total_paragraphs,
                denominator=max(1.0, total_weighted_words / 100.0),
                unit="paragraphs_per_100_words",
            ),
            self._build_ratio_feature(
                feature_key="list_usage",
                section_key="formatting",
                title="List usage",
                items=all_items,
                numerator=total_lists,
                denominator=len(all_items),
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="line_break_frequency",
                section_key="formatting",
                title="Line break frequency",
                items=all_items,
                numerator=sum(item.item.text_reference.count("\n") for item in all_items if item.item.text_reference),
                denominator=len(all_items),
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="first_person_ratio",
                section_key="voice_usage",
                title="First person ratio",
                items=all_items,
                numerator=total_first_person,
                denominator=total_tokens,
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="second_person_ratio",
                section_key="voice_usage",
                title="Second person ratio",
                items=all_items,
                numerator=total_second_person,
                denominator=total_tokens,
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="question_ratio",
                section_key="voice_usage",
                title="Question ratio",
                items=all_items,
                numerator=total_questions,
                denominator=total_sentences,
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="exclamation_ratio",
                section_key="punctuation",
                title="Exclamation ratio",
                items=all_items,
                numerator=total_exclamations,
                denominator=total_sentences,
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="ellipsis_ratio",
                section_key="punctuation",
                title="Ellipsis usage ratio",
                items=all_items,
                numerator=total_ellipsis,
                denominator=len(all_items),
                unit="ratio",
            ),
            self._build_ratio_feature(
                feature_key="lexical_diversity",
                section_key="lexical",
                title="Lexical diversity",
                items=all_items,
                numerator=unique_tokens,
                denominator=total_tokens,
                unit="ratio",
            ),
            self._build_repeated_phrase_feature(section_key="lexical", items=all_items),
        ]

        if spoken_items:
            features.extend(
                [
                    self._build_numeric_feature(
                        feature_key="spoken_median_sentence_length",
                        section_key="spoken",
                        title="Spoken median sentence length",
                        items=spoken_items,
                        values=[(float(length), item.weight) for item in spoken_items for length in item.sentence_lengths],
                        unit="words",
                    ),
                    self._build_ratio_feature(
                        feature_key="spoken_filler_rate",
                        section_key="spoken",
                        title="Spoken filler rate",
                        items=spoken_items,
                        numerator=spoken_filler_weight,
                        denominator=spoken_word_weight,
                        unit="ratio",
                    ),
                ]
            )

        return tuple(features)

    def _section_summary(self, section_key: str, features: tuple[CreatorVoiceFeature, ...], language: str | None) -> str:
        if language == "en":
            prefix = {
                "length": "Typical length leans",
                "sentence_structure": "Sentence structure leans",
                "formatting": "Formatting tends",
                "voice_usage": "Voice usage tends",
                "punctuation": "Punctuation tends",
                "lexical": "Lexical patterns suggest",
                "spoken": "Spoken evidence suggests",
            }.get(section_key, "Observed patterns suggest")
        else:
            prefix = {
                "length": "La longitud suele",
                "sentence_structure": "La estructura de frases suele",
                "formatting": "El formato suele",
                "voice_usage": "El uso de voz suele",
                "punctuation": "La puntuacion suele",
                "lexical": "Los patrones lexicales sugieren",
                "spoken": "La evidencia hablada sugiere",
            }.get(section_key, "Los patrones observados sugieren")
        ready_features = [feature for feature in features if feature.status == CreatorVoiceFeatureStatus.READY]
        if ready_features:
            return f"{prefix} {len(ready_features)} rasgos con evidencia suficiente."
        if features:
            return f"{prefix} rasgos parciales con evidencia limitada."
        return "Sin suficiente evidencia para esta seccion."

    def _section_status(self, features: tuple[CreatorVoiceFeature, ...]) -> CreatorVoiceProfileStatus:
        statuses = {feature.status for feature in features}
        if not statuses:
            return CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE
        if statuses == {CreatorVoiceFeatureStatus.READY}:
            return CreatorVoiceProfileStatus.READY
        if statuses == {CreatorVoiceFeatureStatus.INSUFFICIENT_EVIDENCE}:
            return CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE
        return CreatorVoiceProfileStatus.PARTIAL

    def _section_confidence(self, features: tuple[CreatorVoiceFeature, ...]) -> CreatorVoiceConfidenceLevel:
        if not features:
            return CreatorVoiceConfidenceLevel.LOW
        confidences = [feature.confidence for feature in features]
        if confidences.count(CreatorVoiceConfidenceLevel.HIGH) == len(confidences):
            return CreatorVoiceConfidenceLevel.HIGH
        if confidences.count(CreatorVoiceConfidenceLevel.LOW) == len(confidences):
            return CreatorVoiceConfidenceLevel.LOW
        return CreatorVoiceConfidenceLevel.MEDIUM

    def _build_sections(self, features: tuple[CreatorVoiceFeature, ...], language: str | None) -> tuple[CreatorVoiceProfileSection, ...]:
        by_section: dict[str, list[CreatorVoiceFeature]] = defaultdict(list)
        for feature in features:
            by_section[feature.section_key].append(feature)
        ordered_keys = ("length", "sentence_structure", "formatting", "voice_usage", "punctuation", "lexical", "spoken")
        sections: list[CreatorVoiceProfileSection] = []
        for section_key in ordered_keys:
            section_features = tuple(by_section.get(section_key, ()))
            sections.append(
                CreatorVoiceProfileSection(
                    id=_stable_id("voice-section", section_key, tuple(feature.id for feature in section_features)),
                    section_key=section_key,
                    title=section_key.replace("_", " ").title(),
                    summary=self._section_summary(section_key, section_features, language),
                    status=self._section_status(section_features),
                    confidence=self._section_confidence(section_features),
                    features=section_features,
                    warnings=tuple(
                        warning
                        for feature in section_features
                        for warning in feature.warnings
                    ),
                )
            )
        return tuple(sections)

    def _build_profile_summary(self, profile: CreatorVoiceProfile, language: str | None) -> str:
        feature_map = {feature.feature_key: feature for section in profile.sections for feature in section.features}
        phrases: list[str] = []
        length_feature = feature_map.get("typical_word_count")
        sentence_feature = feature_map.get("median_sentence_length")
        spoken_feature = feature_map.get("spoken_median_sentence_length")
        if language == "en":
            base = {
                CreatorVoiceProfileStatus.READY: "Voice profile ready.",
                CreatorVoiceProfileStatus.PARTIAL: "Voice profile partial.",
                CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE: "Voice profile needs more evidence.",
            }[profile.status]
            phrases.append(base)
            if isinstance(length_feature, CreatorVoiceFeature) and isinstance(length_feature.value, dict):
                median_words = length_feature.value.get("median")
                if isinstance(median_words, (int, float)) and median_words <= 14:
                    phrases.append("The content tends to be concise.")
                elif isinstance(median_words, (int, float)) and median_words >= 22:
                    phrases.append("The content tends to run long.")
            if isinstance(sentence_feature, CreatorVoiceFeature) and isinstance(sentence_feature.value, dict):
                median_sentence = sentence_feature.value.get("median")
                if isinstance(median_sentence, (int, float)) and median_sentence <= 10:
                    phrases.append("Sentences tend to be short.")
                elif isinstance(median_sentence, (int, float)) and median_sentence >= 18:
                    phrases.append("Sentences tend to be long.")
            if isinstance(spoken_feature, CreatorVoiceFeature) and isinstance(spoken_feature.value, dict):
                spoken_median = spoken_feature.value.get("median")
                if isinstance(spoken_median, (int, float)):
                    phrases.append("Spoken evidence is tracked separately.")
        else:
            base = {
                CreatorVoiceProfileStatus.READY: "Perfil de voz listo.",
                CreatorVoiceProfileStatus.PARTIAL: "Perfil de voz parcial.",
                CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE: "Perfil de voz con evidencia insuficiente.",
            }[profile.status]
            phrases.append(base)
            if isinstance(length_feature, CreatorVoiceFeature) and isinstance(length_feature.value, dict):
                median_words = length_feature.value.get("median")
                if isinstance(median_words, (int, float)) and median_words <= 14:
                    phrases.append("Tu contenido suele ser breve.")
                elif isinstance(median_words, (int, float)) and median_words >= 22:
                    phrases.append("Tu contenido suele ser largo.")
            if isinstance(sentence_feature, CreatorVoiceFeature) and isinstance(sentence_feature.value, dict):
                median_sentence = sentence_feature.value.get("median")
                if isinstance(median_sentence, (int, float)) and median_sentence <= 10:
                    phrases.append("Sueles usar frases cortas.")
                elif isinstance(median_sentence, (int, float)) and median_sentence >= 18:
                    phrases.append("Sueles usar frases largas.")
            if profile.structured_preferences:
                phrases.append("Las preferencias confirmadas se conservan por separado.")
        return " ".join(phrases)

    def _build_warnings(self, snapshot: CreatorVoiceEvidenceSnapshot, profile_status: CreatorVoiceProfileStatus, structured_preferences: tuple[CreatorVoiceStructuredPreference, ...]) -> tuple[str, ...]:
        warnings = [f"snapshot_policy={snapshot.policy_version.value}"]
        if profile_status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
            warnings.append("insufficient_evidence")
        if structured_preferences and any(pref.conflict for pref in structured_preferences):
            warnings.append("confirmed_preference_conflict")
        if snapshot.language is None:
            warnings.append("language_unset")
        if len(snapshot.language_distribution) > 1:
            warnings.append("mixed_language_evidence")
        return tuple(dict.fromkeys(warnings))

    def _build_limitations(self, snapshot: CreatorVoiceEvidenceSnapshot, profile_status: CreatorVoiceProfileStatus) -> tuple[str, ...]:
        limitations = [
            "No personality, ideology, or sensitive trait inference.",
            "No prompt application yet.",
            "No retrieval mutation yet.",
            "No embeddings or fine-tuning.",
        ]
        if profile_status != CreatorVoiceProfileStatus.READY:
            limitations.append("Evidence volume is below the ready threshold.")
        if snapshot.excluded_counts:
            limitations.append("Excluded evidence remains outside the profile.")
        return tuple(limitations)

    def build_profile(self, snapshot: CreatorVoiceEvidenceSnapshot) -> CreatorVoiceProfile:
        if not isinstance(snapshot, CreatorVoiceEvidenceSnapshot):
            raise TypeError("snapshot must be a CreatorVoiceEvidenceSnapshot.")
        text_items = []
        for item in self._profile_items(snapshot):
            analyzed = self._analyze_item(item)
            if analyzed is not None:
                text_items.append(analyzed)
        features = self._all_features(text_items)
        sections = self._build_sections(features, snapshot.language)
        structured_preferences = self._build_structured_preferences(snapshot, text_items)
        evidence_words = sum(item.word_count * item.weight for item in text_items)
        source_count = len({item.item.source_identity for item in text_items})
        status = _profile_status(evidence_words=evidence_words, source_count=source_count)
        confidence = _profile_confidence(
            status=status,
            section_confidence_values=[section.confidence for section in sections],
            warnings=tuple(pref.warning for pref in structured_preferences if pref.warning),
        )
        warning_list: list[str] = []
        if snapshot.language_distribution and len(snapshot.language_distribution) > 1:
            warning_list.append("mixed_language_evidence")
        if snapshot.excluded_counts.get("ai_generated") or snapshot.excluded_counts.get("ai_rewritten"):
            warning_list.append("ai_contamination_blocked")
        if any(pref.conflict for pref in structured_preferences):
            warning_list.append("confirmed_preference_conflict")
        if status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
            warning_list.append("insufficient_evidence")
        limitations = self._build_limitations(snapshot, status)
        profile = CreatorVoiceProfile(
            creator_id=snapshot.creator_id,
            project_id=snapshot.project_id,
            workflow_type=snapshot.workflow_type,
            language=snapshot.language,
            profile_version=self.PROFILE_VERSION,
            feature_algorithm_version=self.FEATURE_ALGORITHM_VERSION,
            evidence_snapshot_fingerprint=snapshot.content_fingerprint,
            generated_at=utc_now(),
            evidence_count=len(text_items),
            confidence_summary=confidence,
            status=status,
            sections=sections,
            structured_preferences=structured_preferences,
            warnings=tuple(dict.fromkeys(warning_list)),
            limitations=limitations,
            summary="",
            fingerprint="",
        )
        summary = self._build_profile_summary(profile, snapshot.language)
        fingerprint_payload = {
            "evidence_snapshot_fingerprint": snapshot.content_fingerprint,
            "profile_version": profile.profile_version.value,
            "feature_algorithm_version": profile.feature_algorithm_version,
            "status": profile.status.value,
            "confidence_summary": profile.confidence_summary.value,
            "features": [feature.to_dict() for feature in features],
            "structured_preferences": [preference.to_dict() for preference in structured_preferences],
            "warnings": list(profile.warnings),
            "limitations": list(profile.limitations),
        }
        fingerprint = _hash_text(_stable_json(fingerprint_payload))
        return CreatorVoiceProfile(
            creator_id=profile.creator_id,
            project_id=profile.project_id,
            workflow_type=profile.workflow_type,
            language=profile.language,
            profile_version=profile.profile_version,
            feature_algorithm_version=profile.feature_algorithm_version,
            evidence_snapshot_fingerprint=profile.evidence_snapshot_fingerprint,
            generated_at=profile.generated_at,
            evidence_count=profile.evidence_count,
            confidence_summary=profile.confidence_summary,
            status=profile.status,
            sections=profile.sections,
            structured_preferences=profile.structured_preferences,
            warnings=profile.warnings,
            limitations=profile.limitations,
            summary=summary,
            fingerprint=fingerprint,
        )

    def compare_profiles(self, base: CreatorVoiceProfile, compare: CreatorVoiceProfile) -> CreatorVoiceProfileComparison:
        if base.creator_id != compare.creator_id:
            raise ValueError("Profiles must belong to the same creator to compare.")
        base_features = {feature.feature_key: feature for section in base.sections for feature in section.features}
        compare_features = {feature.feature_key: feature for section in compare.sections for feature in section.features}
        changed_features = tuple(
            sorted(
                key
                for key in set(base_features) | set(compare_features)
                if base_features.get(key) is None or compare_features.get(key) is None or base_features[key].to_dict() != compare_features[key].to_dict()
            )
        )
        changed_sections = tuple(
            sorted(
                section_key
                for section_key in set(section.section_key for section in base.sections) | set(section.section_key for section in compare.sections)
                if {
                    feature.feature_key: feature.to_dict()
                    for feature in next((section.features for section in base.sections if section.section_key == section_key), ())
                }
                != {
                    feature.feature_key: feature.to_dict()
                    for feature in next((section.features for section in compare.sections if section.section_key == section_key), ())
                }
            )
        )
        summary = f"{len(changed_features)} rasgos cambiaron entre {base.profile_version.value} y {compare.profile_version.value}."
        return CreatorVoiceProfileComparison(
            creator_id=base.creator_id,
            base_profile_fingerprint=base.fingerprint,
            compare_profile_fingerprint=compare.fingerprint,
            changed_sections=changed_sections,
            changed_features=changed_features,
            summary=summary,
        )

    def diagnostics(self, profile: CreatorVoiceProfile, *, debug: bool = False) -> dict[str, object]:
        payload = profile.to_dict()
        if not debug:
            payload["structured_preferences"] = [item for item in payload["structured_preferences"]]
        return {
            "profile": payload,
            "summary": {
                "creator_id": profile.creator_id,
                "project_id": profile.project_id,
                "workflow_type": profile.workflow_type,
                "language": profile.language,
                "profile_version": profile.profile_version.value,
                "status": profile.status.value,
                "confidence_summary": profile.confidence_summary.value,
                "fingerprint": profile.fingerprint,
            },
        }


def build_creator_voice_profile_service(*, logger: logging.Logger | None = None) -> CreatorVoiceProfileService:
    return CreatorVoiceProfileService(logger=logger)
