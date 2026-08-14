"""Deterministic Creator Voice guidance consumption."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from creator_intelligence_studio.domain.creator_voice import (
    CreatorVoiceConfidenceLevel,
    CreatorVoiceFeature,
    CreatorVoiceFeatureStatus,
    CreatorVoiceGuidanceBundle,
    CreatorVoiceGuidanceCategory,
    CreatorVoiceGuidanceConflict,
    CreatorVoiceGuidanceItem,
    CreatorVoiceGuidanceOmission,
    CreatorVoiceGuidanceOmissionReason,
    CreatorVoiceGuidanceRequest,
    CreatorVoiceGuidanceState,
    CreatorVoiceGuidanceVersion,
    CreatorVoiceProfile,
    CreatorVoiceProfileStatus,
    CreatorVoiceProfileVersion,
    CreatorVoiceScopeMode,
    CreatorVoiceStructuredPreference,
)
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.shared.dates import utc_now


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _stable_id(*parts: object) -> str:
    return sha256(_json_dumps(parts).encode("utf-8")).hexdigest()


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _language_key(value: str | None) -> str | None:
    normalized = _normalize_text(value).replace("_", "-").lower()
    return normalized or None


def _workflow_mode(workflow_type: str) -> str:
    normalized = _normalize_text(workflow_type).lower()
    spoken_tokens = (
        "spoken",
        "speech",
        "audio",
        "transcript",
        "podcast",
        "voice",
        "talk",
        "conversation",
        "interview",
    )
    if any(token in normalized for token in spoken_tokens):
        return "spoken"
    return "written"


def _infer_length_direction(text: str | None) -> str | None:
    normalized = _normalize_text(text).casefold()
    if not normalized:
        return None
    shorter_tokens = (
        "short",
        "shorter",
        "brief",
        "concise",
        "breve",
        "breves",
        "corto",
        "corta",
        "cortos",
        "cortas",
        "conciso",
        "concisa",
        "compact",
        "tight",
        "summar",
        "reduce",
        "less",
        "under 15",
        "15 seconds",
    )
    longer_tokens = (
        "long",
        "longer",
        "largo",
        "larga",
        "largos",
        "largas",
        "detailed",
        "detallado",
        "detallada",
        "expanded",
        "comprehensive",
        "cinematic",
        "thorough",
        "more detail",
    )
    shorter = any(token in normalized for token in shorter_tokens)
    longer = any(token in normalized for token in longer_tokens)
    if shorter and longer:
        return None
    if shorter:
        return "shorter"
    if longer:
        return "longer"
    return None


def _feature_map(profile: CreatorVoiceProfile) -> dict[str, CreatorVoiceFeature]:
    return {
        feature.feature_key: feature
        for section in profile.sections
        for feature in section.features
    }


def _preference_direction(preference: CreatorVoiceStructuredPreference) -> str | None:
    direction = str(preference.value.get("direction") or "").strip().lower()
    if direction in {"shorter", "longer"}:
        return direction
    return None


def _preference_scope_label(scope: CreatorVoiceScopeMode) -> str:
    return {
        CreatorVoiceScopeMode.CREATOR_GLOBAL: "creator_global",
        CreatorVoiceScopeMode.PROJECT_SPECIFIC: "project_specific",
        CreatorVoiceScopeMode.WORKFLOW_SPECIFIC: "workflow_specific",
    }[scope]


def _guidance_state_for_profile(status: CreatorVoiceProfileStatus) -> CreatorVoiceGuidanceState:
    return {
        CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE: CreatorVoiceGuidanceState.INSUFFICIENT_PROFILE,
        CreatorVoiceProfileStatus.PARTIAL: CreatorVoiceGuidanceState.PARTIAL,
        CreatorVoiceProfileStatus.READY: CreatorVoiceGuidanceState.READY,
    }[status]


@dataclass(frozen=True, slots=True)
class _GuidanceRule:
    source_feature_key: str
    guidance_key: str
    category: CreatorVoiceGuidanceCategory
    priority: int
    modes: tuple[str, ...]
    conservative: bool
    renderer_key: str
    max_confidence: CreatorVoiceConfidenceLevel = CreatorVoiceConfidenceLevel.HIGH


class CreatorVoiceGuidanceService:
    GUIDANCE_VERSION = CreatorVoiceGuidanceVersion.V1
    FEATURE_ALGORITHM_VERSION = "creator-voice-guidance-feature-v1"
    MAX_ITEMS = 4
    MAX_CHARACTERS = 480

    _RULES: tuple[_GuidanceRule, ...] = (
        _GuidanceRule(
            source_feature_key="typical_word_count",
            guidance_key="intro_length_tendency",
            category=CreatorVoiceGuidanceCategory.LENGTH,
            priority=100,
            modes=("written", "spoken"),
            conservative=True,
            renderer_key="intro_length",
        ),
        _GuidanceRule(
            source_feature_key="median_sentence_length",
            guidance_key="sentence_length_tendency",
            category=CreatorVoiceGuidanceCategory.SENTENCE_STRUCTURE,
            priority=90,
            modes=("written", "spoken"),
            conservative=True,
            renderer_key="sentence_length",
        ),
        _GuidanceRule(
            source_feature_key="paragraph_density",
            guidance_key="paragraph_density",
            category=CreatorVoiceGuidanceCategory.FORMATTING,
            priority=80,
            modes=("written",),
            conservative=True,
            renderer_key="paragraph_density",
        ),
        _GuidanceRule(
            source_feature_key="question_ratio",
            guidance_key="question_usage",
            category=CreatorVoiceGuidanceCategory.INTERACTION_STYLE,
            priority=70,
            modes=("written", "spoken"),
            conservative=False,
            renderer_key="question_usage",
            max_confidence=CreatorVoiceConfidenceLevel.MEDIUM,
        ),
        _GuidanceRule(
            source_feature_key="spoken_median_sentence_length",
            guidance_key="spoken_sentence_length_tendency",
            category=CreatorVoiceGuidanceCategory.SPOKEN,
            priority=95,
            modes=("spoken",),
            conservative=True,
            renderer_key="spoken_sentence_length",
        ),
        _GuidanceRule(
            source_feature_key="spoken_filler_rate",
            guidance_key="spoken_filler_pattern",
            category=CreatorVoiceGuidanceCategory.SPOKEN,
            priority=85,
            modes=("spoken",),
            conservative=False,
            renderer_key="spoken_filler_rate",
            max_confidence=CreatorVoiceConfidenceLevel.MEDIUM,
        ),
    )

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_voice_guidance")

    @staticmethod
    def audit_supported_guidance_matrix() -> tuple[dict[str, object], ...]:
        return (
            {
                "source_feature_key": "typical_word_count",
                "guidance_key": "intro_length_tendency",
                "category": CreatorVoiceGuidanceCategory.LENGTH.value,
                "safe_human_wording": "Preferir introducciones mas concisas o mas desarrolladas cuando no contradiga la solicitud actual.",
                "why": "Es una tendencia estructural observable y controlable.",
            },
            {
                "source_feature_key": "median_sentence_length",
                "guidance_key": "sentence_length_tendency",
                "category": CreatorVoiceGuidanceCategory.SENTENCE_STRUCTURE.value,
                "safe_human_wording": "Ajustar la longitud de las frases en la direccion observada cuando sea compatible.",
                "why": "Es una pauta formal, no una inferencia de personalidad.",
            },
            {
                "source_feature_key": "paragraph_density",
                "guidance_key": "paragraph_density",
                "category": CreatorVoiceGuidanceCategory.FORMATTING.value,
                "safe_human_wording": "Conservar la densidad de parrafos cuando la tarea lo permita.",
                "why": "Es una tendencia de formato determinista.",
            },
            {
                "source_feature_key": "question_ratio",
                "guidance_key": "question_usage",
                "category": CreatorVoiceGuidanceCategory.INTERACTION_STYLE.value,
                "safe_human_wording": "Usar preguntas con moderacion o mas frecuentemente, segun el patron observado.",
                "why": "Es una pauta de interaccion observable.",
            },
            {
                "source_feature_key": "spoken_median_sentence_length",
                "guidance_key": "spoken_sentence_length_tendency",
                "category": CreatorVoiceGuidanceCategory.SPOKEN.value,
                "safe_human_wording": "Preservar la diferencia entre patrones hablados y escritos.",
                "why": "Se consume solo cuando el flujo de trabajo es hablado.",
            },
        )

    def _profile_scope_matches(self, request: CreatorVoiceGuidanceRequest, profile: CreatorVoiceProfile) -> tuple[bool, CreatorVoiceGuidanceOmissionReason | None, str | None]:
        if request.creator_id != profile.creator_id:
            raise DomainError("Creator mismatch between guidance request and profile.")
        if profile.project_id is not None and request.project_id != profile.project_id:
            return False, CreatorVoiceGuidanceOmissionReason.WRONG_SCOPE, "profile_project_scope_does_not_match_request"
        if profile.workflow_type is not None and _normalize_text(request.workflow_type).lower() != _normalize_text(profile.workflow_type).lower():
            return False, CreatorVoiceGuidanceOmissionReason.WRONG_SCOPE, "profile_workflow_scope_does_not_match_request"
        request_language = _language_key(request.language)
        profile_language = _language_key(profile.language)
        if request_language is not None and profile_language is not None and request_language != profile_language:
            return False, CreatorVoiceGuidanceOmissionReason.WRONG_LANGUAGE, "profile_language_does_not_match_request"
        return True, None, None

    def _confidence_allowed(self, *, profile_status: CreatorVoiceProfileStatus, feature: CreatorVoiceFeature, rule: _GuidanceRule) -> bool:
        if feature.status == CreatorVoiceFeatureStatus.INSUFFICIENT_EVIDENCE:
            return False
        if feature.confidence == CreatorVoiceConfidenceLevel.LOW:
            return False
        if profile_status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
            return False
        if profile_status == CreatorVoiceProfileStatus.PARTIAL:
            return feature.confidence == CreatorVoiceConfidenceLevel.HIGH and feature.status == CreatorVoiceFeatureStatus.READY
        if profile_status == CreatorVoiceProfileStatus.READY:
            if feature.confidence == CreatorVoiceConfidenceLevel.HIGH:
                return True
            return rule.conservative and feature.confidence == CreatorVoiceConfidenceLevel.MEDIUM and feature.status != CreatorVoiceFeatureStatus.INSUFFICIENT_EVIDENCE
        return False

    def _render_guidance_text(self, *, feature: CreatorVoiceFeature, rule: _GuidanceRule, language: str | None) -> str | None:
        value = feature.value if isinstance(feature.value, dict) else {}
        if rule.renderer_key == "intro_length":
            median_words = value.get("median")
            if not isinstance(median_words, (int, float)):
                return None
            if median_words <= 14:
                return {
                    "en": "Prefer relatively concise introductions when compatible with the current request.",
                    "es": "Prefiere introducciones relativamente concisas cuando sea compatible con la solicitud actual.",
                }.get(language or "", "Prefer relatively concise introductions when compatible with the current request.")
            if median_words >= 22:
                return {
                    "en": "Allow a more developed introduction when the task permits it.",
                    "es": "Permite una introduccion mas desarrollada cuando la tarea lo permita.",
                }.get(language or "", "Allow a more developed introduction when the task permits it.")
            return None
        if rule.renderer_key == "sentence_length":
            median_sentence = value.get("median")
            if not isinstance(median_sentence, (int, float)):
                return None
            if median_sentence <= 10:
                return {
                    "en": "Favor shorter sentences in written content.",
                    "es": "Favorece frases mas cortas en el contenido escrito.",
                }.get(language or "", "Favor shorter sentences in written content.")
            if median_sentence >= 18:
                return {
                    "en": "Allow longer sentences when the request benefits from a broader cadence.",
                    "es": "Permite frases mas largas cuando la solicitud se beneficie de un ritmo mas amplio.",
                }.get(language or "", "Allow longer sentences when the request benefits from a broader cadence.")
            return None
        if rule.renderer_key == "paragraph_density":
            median_paragraphs = value.get("median")
            if not isinstance(median_paragraphs, (int, float)):
                return None
            if median_paragraphs >= 4:
                return {
                    "en": "Use more paragraph breaks when the task calls for a readable structure.",
                    "es": "Usa mas saltos de parrafo cuando la tarea pida una estructura mas legible.",
                }.get(language or "", "Use more paragraph breaks when the task calls for a readable structure.")
            if median_paragraphs <= 2:
                return {
                    "en": "Keep paragraphs relatively compact unless the request asks otherwise.",
                    "es": "Mantiene los parrafos relativamente compactos salvo que la solicitud pida otra cosa.",
                }.get(language or "", "Keep paragraphs relatively compact unless the request asks otherwise.")
            return None
        if rule.renderer_key == "question_usage":
            ratio = value.get("ratio")
            if not isinstance(ratio, (int, float)):
                return None
            if ratio >= 0.18:
                return {
                    "en": "Questions are common in this voice; use them with a light, deliberate rhythm.",
                    "es": "Las preguntas son comunes en esta voz; usalas con un ritmo ligero y deliberado.",
                }.get(language or "", "Questions are common in this voice; use them with a light, deliberate rhythm.")
            if ratio <= 0.05:
                return {
                    "en": "Use questions sparingly.",
                    "es": "Usa preguntas con moderacion.",
                }.get(language or "", "Use questions sparingly.")
            return None
        if rule.renderer_key == "spoken_sentence_length":
            median_sentence = value.get("median")
            if not isinstance(median_sentence, (int, float)):
                return None
            if median_sentence <= 12:
                return {
                    "en": "Keep spoken phrasing relatively concise.",
                    "es": "Mantiene una formulacion hablada relativamente concisa.",
                }.get(language or "", "Keep spoken phrasing relatively concise.")
            if median_sentence >= 20:
                return {
                    "en": "Allow longer spoken sentences when delivery stays clear.",
                    "es": "Permite frases habladas mas largas cuando la entrega siga siendo clara.",
                }.get(language or "", "Allow longer spoken sentences when delivery stays clear.")
            return None
        if rule.renderer_key == "spoken_filler_rate":
            ratio = value.get("ratio")
            if not isinstance(ratio, (int, float)):
                return None
            if ratio >= 0.08:
                return {
                    "en": "Preserve conversational fillers only when they support the spoken cadence.",
                    "es": "Conserva muletillas conversacionales solo cuando apoyen el ritmo hablado.",
                }.get(language or "", "Preserve conversational fillers only when they support the spoken cadence.")
            return None
        return None

    def _structured_preference_override(
        self,
        *,
        feature: CreatorVoiceFeature,
        profile: CreatorVoiceProfile,
        request: CreatorVoiceGuidanceRequest,
    ) -> tuple[bool, CreatorVoiceGuidanceOmissionReason | None, CreatorVoiceStructuredPreference | None, str | None]:
        if feature.feature_key not in {"typical_word_count", "median_sentence_length", "paragraph_density", "question_ratio", "spoken_median_sentence_length", "spoken_filler_rate"}:
            return False, None, None, None
        if feature.feature_key not in {"typical_word_count", "median_sentence_length"}:
            return False, None, None, None
        preferences = [
            preference
            for preference in profile.structured_preferences
            if preference.preference_type == "content_length_preference"
        ]
        request_direction = _infer_length_direction(request.current_user_instruction)
        project_direction = _infer_length_direction(request.project_instruction)
        if request_direction:
            return True, CreatorVoiceGuidanceOmissionReason.USER_OVERRIDE, None, request_direction
        if project_direction:
            return True, CreatorVoiceGuidanceOmissionReason.PROJECT_OVERRIDE, None, project_direction
        if not preferences:
            return False, None, None, None
        return True, CreatorVoiceGuidanceOmissionReason.PREFERENCE_OVERRIDE, preferences[0], _preference_direction(preferences[0])

    def _build_guidance_item(
        self,
        *,
        request: CreatorVoiceGuidanceRequest,
        profile: CreatorVoiceProfile,
        feature: CreatorVoiceFeature,
        rule: _GuidanceRule,
        language: str | None,
    ) -> tuple[CreatorVoiceGuidanceItem | None, CreatorVoiceGuidanceOmission | None, CreatorVoiceGuidanceConflict | None]:
        if feature.status == CreatorVoiceFeatureStatus.INSUFFICIENT_EVIDENCE:
            omission = CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, rule.guidance_key, feature.id, "insufficient_feature"),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=rule.category,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                reason=CreatorVoiceGuidanceOmissionReason.LOW_CONFIDENCE,
                detail="feature_status_insufficient",
                scope=feature.evidence_basis.get("scope") if isinstance(feature.evidence_basis, dict) else None,
                confidence=feature.confidence,
                profile_status=profile.status,
                evidence_item_count=feature.evidence_item_count,
            )
            return None, omission, None
        if request.workflow_type and _workflow_mode(request.workflow_type) not in rule.modes:
            omission = CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, rule.guidance_key, feature.id, "wrong_scope"),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=rule.category,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                reason=CreatorVoiceGuidanceOmissionReason.WRONG_SCOPE,
                detail="workflow_mode_not_supported",
                scope=None,
                confidence=feature.confidence,
                profile_status=profile.status,
                evidence_item_count=feature.evidence_item_count,
            )
            return None, omission, None
        if not self._confidence_allowed(profile_status=profile.status, feature=feature, rule=rule):
            omission = CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, rule.guidance_key, feature.id, "low_confidence"),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=rule.category,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                reason=CreatorVoiceGuidanceOmissionReason.LOW_CONFIDENCE,
                detail="confidence_not_safe_for_guidance",
                scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                    CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                ),
                confidence=feature.confidence,
                profile_status=profile.status,
                evidence_item_count=feature.evidence_item_count,
            )
            return None, omission, None
        if profile.language is not None and language is not None and _language_key(profile.language) != _language_key(language):
            omission = CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, rule.guidance_key, feature.id, "wrong_language"),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=rule.category,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                reason=CreatorVoiceGuidanceOmissionReason.WRONG_LANGUAGE,
                detail="profile_language_not_compatible_with_request",
                scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                    CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                ),
                confidence=feature.confidence,
                profile_status=profile.status,
                evidence_item_count=feature.evidence_item_count,
            )
            return None, omission, None
        override_applies, override_reason, preference, override_direction = self._structured_preference_override(feature=feature, profile=profile, request=request)
        if override_applies:
            detail = override_reason.value if override_reason else "override"
            omission = CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, rule.guidance_key, feature.id, detail),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=rule.category,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                reason=override_reason or CreatorVoiceGuidanceOmissionReason.PROFILE_CONFLICT,
                detail=detail,
                scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                    CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                ),
                confidence=feature.confidence,
                profile_status=profile.status,
                evidence_item_count=feature.evidence_item_count,
            )
            conflict = CreatorVoiceGuidanceConflict(
                id=_stable_id("conflict", request.creator_id, rule.guidance_key, feature.id, detail),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                override_type=detail,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                blocker_text=request.current_user_instruction or request.project_instruction or (preference.rendered_text if preference else ""),
                scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                    CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                ),
                request_scope="creator_global" if request.project_id is None and request.workflow_type else "scoped",
                profile_status=profile.status,
                profile_confidence=profile.confidence_summary,
                reason=detail,
                evidence_item_count=feature.evidence_item_count,
            )
            return None, omission, conflict
        guidance_text = self._render_guidance_text(feature=feature, rule=rule, language=language)
        if not guidance_text:
            omission = CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, rule.guidance_key, feature.id, "too_little_signal"),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=rule.category,
                guidance_key=rule.guidance_key,
                source_feature_id=feature.id,
                source_feature_key=feature.feature_key,
                reason=CreatorVoiceGuidanceOmissionReason.TOO_LITTLE_SIGNAL,
                detail="feature_value_is_not_strong_enough_for_guidance",
                scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                    CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                ),
                confidence=feature.confidence,
                profile_status=profile.status,
                evidence_item_count=feature.evidence_item_count,
            )
            return None, omission, None
        item = CreatorVoiceGuidanceItem(
            id=_stable_id("guidance-item", request.creator_id, rule.guidance_key, feature.id, language or ""),
            creator_id=request.creator_id,
            project_id=request.project_id,
            workflow_type=request.workflow_type,
            language=language,
            category=rule.category,
            guidance_key=rule.guidance_key,
            source_feature_id=feature.id,
            source_feature_key=feature.feature_key,
            source_feature_title=feature.title,
            scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
            ),
            profile_status=profile.status,
            profile_version=profile.profile_version,
            confidence=feature.confidence,
            feature_status=feature.status.value,
            evidence_item_count=feature.evidence_item_count,
            independent_source_count=feature.independent_source_count,
            source_feature_ids=tuple(str(item_id) for item_id in feature.evidence_basis.get("supporting_item_ids", [])[:5]) if isinstance(feature.evidence_basis, dict) else (),
            source_feature_value=feature.value,
            source_feature_basis=dict(feature.evidence_basis),
            guidance_text=guidance_text,
            warnings=tuple(feature.warnings),
        )
        return item, None, None

    def _render_bundle(self, items: tuple[CreatorVoiceGuidanceItem, ...], *, language: str | None, profile_status: CreatorVoiceProfileStatus | None) -> str:
        if not items:
            if language and _language_key(language) == "es":
                if profile_status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
                    return "No se emitio guia de Creator Voice porque la evidencia es insuficiente."
                return "No se emitio guia de Creator Voice."
            if profile_status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
                return "No Creator Voice guidance was emitted because evidence is insufficient."
            return "No Creator Voice guidance was emitted."
        lines = ["CREATOR VOICE GUIDANCE"]
        for item in items:
            lines.append(f"- {item.guidance_text}")
        if language and _language_key(language) == "es":
            lines.append("Esta guia es secundaria a la solicitud actual, las instrucciones del proyecto y las preferencias confirmadas.")
        else:
            lines.append("This guidance is secondary to the current request, project instructions, and confirmed preferences.")
        rendered = "\n".join(lines).strip()
        if len(rendered) > self.MAX_CHARACTERS:
            return rendered[: self.MAX_CHARACTERS].rstrip() + "..."
        return rendered

    def build_guidance(self, request: CreatorVoiceGuidanceRequest | dict[str, object]) -> CreatorVoiceGuidanceBundle:
        normalized_request = self._normalize_request(request)
        if not normalized_request.enabled:
            return self._empty_bundle(normalized_request, CreatorVoiceGuidanceState.DISABLED, CreatorVoiceGuidanceOmissionReason.DISABLED, "guidance_disabled")
        profile = normalized_request.profile
        if profile is None:
            return self._empty_bundle(normalized_request, CreatorVoiceGuidanceState.MISSING_PROFILE, CreatorVoiceGuidanceOmissionReason.MISSING_PROFILE, "profile_missing")
        if not isinstance(profile, CreatorVoiceProfile):
            raise TypeError("profile must be a CreatorVoiceProfile or None.")
        if profile.creator_id != normalized_request.creator_id:
            raise DomainError("Creator mismatch between guidance request and profile.")
        scope_ok, reason, detail = self._profile_scope_matches(normalized_request, profile)
        if not scope_ok and reason is not None:
            return self._empty_bundle(normalized_request, CreatorVoiceGuidanceState.MISSING_PROFILE if reason == CreatorVoiceGuidanceOmissionReason.MISSING_PROFILE else CreatorVoiceGuidanceState.INSUFFICIENT_PROFILE, reason, detail or reason.value, profile=profile)
        if profile.status == CreatorVoiceProfileStatus.INSUFFICIENT_EVIDENCE:
            return self._empty_bundle(normalized_request, CreatorVoiceGuidanceState.INSUFFICIENT_PROFILE, CreatorVoiceGuidanceOmissionReason.INSUFFICIENT_PROFILE, "profile_insufficient", profile=profile)

        language = _language_key(normalized_request.language or profile.language)
        mode = _workflow_mode(normalized_request.workflow_type)
        features = _feature_map(profile)
        ordered_rules = sorted(self._RULES, key=lambda rule: (-rule.priority, rule.guidance_key))
        guidance_items: list[CreatorVoiceGuidanceItem] = []
        omitted_items: list[CreatorVoiceGuidanceOmission] = []
        conflicts: list[CreatorVoiceGuidanceConflict] = []
        for rule in ordered_rules:
            if len(guidance_items) >= max(0, int(normalized_request.max_items)):
                omitted_items.append(
                    CreatorVoiceGuidanceOmission(
                        id=_stable_id("omission", normalized_request.creator_id, rule.guidance_key, "budget_cap"),
                        creator_id=normalized_request.creator_id,
                        project_id=normalized_request.project_id,
                        workflow_type=normalized_request.workflow_type,
                        language=language,
                        category=rule.category,
                        guidance_key=rule.guidance_key,
                        source_feature_id=None,
                        source_feature_key=rule.source_feature_key,
                        reason=CreatorVoiceGuidanceOmissionReason.TOO_MUCH_GUIDANCE,
                        detail="max_items_reached",
                        scope=CreatorVoiceScopeMode.CREATOR_GLOBAL if profile.project_id is None and profile.workflow_type is None else (
                            CreatorVoiceScopeMode.PROJECT_SPECIFIC if profile.project_id is not None else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                        ),
                        confidence=None,
                        profile_status=profile.status,
                        evidence_item_count=None,
                    )
                )
                continue
            if mode not in rule.modes:
                omitted_items.append(
                    CreatorVoiceGuidanceOmission(
                        id=_stable_id("omission", normalized_request.creator_id, rule.guidance_key, "wrong_mode"),
                        creator_id=normalized_request.creator_id,
                        project_id=normalized_request.project_id,
                        workflow_type=normalized_request.workflow_type,
                        language=language,
                        category=rule.category,
                        guidance_key=rule.guidance_key,
                        source_feature_id=None,
                        source_feature_key=rule.source_feature_key,
                        reason=CreatorVoiceGuidanceOmissionReason.WRONG_SCOPE,
                        detail="workflow_mode_not_supported",
                        scope=None,
                        confidence=None,
                        profile_status=profile.status,
                        evidence_item_count=None,
                    )
                )
                continue
            feature = features.get(rule.source_feature_key)
            if feature is None:
                omitted_items.append(
                    CreatorVoiceGuidanceOmission(
                        id=_stable_id("omission", normalized_request.creator_id, rule.guidance_key, "unsupported_feature"),
                        creator_id=normalized_request.creator_id,
                        project_id=normalized_request.project_id,
                        workflow_type=normalized_request.workflow_type,
                        language=language,
                        category=rule.category,
                        guidance_key=rule.guidance_key,
                        source_feature_id=None,
                        source_feature_key=rule.source_feature_key,
                        reason=CreatorVoiceGuidanceOmissionReason.UNSUPPORTED_FEATURE,
                        detail="feature_not_present_in_profile",
                        scope=None,
                        confidence=None,
                        profile_status=profile.status,
                        evidence_item_count=None,
                    )
                )
                continue
            item, omission, conflict = self._build_guidance_item(
                request=normalized_request,
                profile=profile,
                feature=feature,
                rule=rule,
                language=language,
            )
            if item is not None:
                guidance_items.append(item)
            if omission is not None:
                omitted_items.append(omission)
            if conflict is not None:
                conflicts.append(conflict)

        budget_requested = {
            "max_items": max(0, int(normalized_request.max_items)),
            "max_characters": max(0, int(normalized_request.max_characters)),
        }
        rendered_guidance = self._render_bundle(tuple(guidance_items), language=language, profile_status=profile.status)
        if len(rendered_guidance) > budget_requested["max_characters"]:
            if budget_requested["max_characters"] <= 3:
                rendered_guidance = rendered_guidance[: budget_requested["max_characters"]]
            else:
                rendered_guidance = rendered_guidance[: budget_requested["max_characters"] - 3].rstrip() + "..."
        bundle_fingerprint_payload = {
            "guidance_version": self.GUIDANCE_VERSION.value,
            "profile_fingerprint": profile.fingerprint,
            "profile_status": profile.status.value,
            "profile_version": profile.profile_version.value,
            "creator_id": normalized_request.creator_id,
            "project_id": normalized_request.project_id,
            "workflow_type": normalized_request.workflow_type,
            "language": language,
            "enabled": normalized_request.enabled,
            "budget_requested": budget_requested,
            "guidance_item_ids": [item.id for item in guidance_items],
            "omitted_item_ids": [item.id for item in omitted_items],
            "conflict_ids": [item.id for item in conflicts],
        }
        bundle_fingerprint = _stable_id(bundle_fingerprint_payload)
        warnings = []
        if profile.warnings:
            warnings.extend(profile.warnings)
        if profile.status == CreatorVoiceProfileStatus.PARTIAL:
            warnings.append("partial_profile")
        if profile.status == CreatorVoiceProfileStatus.READY and len(guidance_items) == 0:
            warnings.append("ready_profile_no_consumable_guidance")
        if omitted_items:
            warnings.append("guidance_omissions_present")
        if conflicts:
            warnings.append("guidance_conflicts_present")
        if normalized_request.current_user_instruction:
            warnings.append("current_user_instruction_present")
        if normalized_request.project_instruction:
            warnings.append("project_instruction_present")
        return CreatorVoiceGuidanceBundle(
            creator_id=normalized_request.creator_id,
            project_id=normalized_request.project_id,
            workflow_type=normalized_request.workflow_type,
            language=language,
            guidance_version=self.GUIDANCE_VERSION,
            profile_fingerprint=profile.fingerprint,
            profile_version=profile.profile_version,
            profile_status=profile.status,
            guidance_state=_guidance_state_for_profile(profile.status),
            guidance_items=tuple(guidance_items),
            omitted_items=tuple(omitted_items),
            conflicts=tuple(conflicts),
            warnings=tuple(dict.fromkeys(warnings)),
            budget_requested=budget_requested,
            budget_used={
                "max_items": len(guidance_items),
                "max_characters": len(rendered_guidance),
            },
            rendered_guidance=rendered_guidance,
            request_trace={
                "enabled": normalized_request.enabled,
                "profile_status": profile.status.value,
                "profile_confidence": profile.confidence_summary.value,
                "profile_version": profile.profile_version.value,
                "profile_fingerprint": profile.fingerprint,
                "current_user_override": bool(normalized_request.current_user_instruction and _infer_length_direction(normalized_request.current_user_instruction)),
                "project_override": bool(normalized_request.project_instruction and _infer_length_direction(normalized_request.project_instruction)),
                "guidance_item_ids": [item.id for item in guidance_items],
                "omitted_reasons": [item.reason.value for item in omitted_items],
                "conflicts": [item.to_dict() for item in conflicts],
                "supported_feature_keys": [rule.source_feature_key for rule in ordered_rules],
            },
            bundle_fingerprint=bundle_fingerprint,
            created_at=utc_now(),
        )

    def _empty_bundle(
        self,
        request: CreatorVoiceGuidanceRequest,
        guidance_state: CreatorVoiceGuidanceState,
        omission_reason: CreatorVoiceGuidanceOmissionReason,
        detail: str,
        *,
        profile: CreatorVoiceProfile | None = None,
    ) -> CreatorVoiceGuidanceBundle:
        language = _language_key(request.language or (profile.language if profile else None))
        omitted = (
            CreatorVoiceGuidanceOmission(
                id=_stable_id("omission", request.creator_id, omission_reason.value, detail, request.workflow_type, request.project_id or "", language or ""),
                creator_id=request.creator_id,
                project_id=request.project_id,
                workflow_type=request.workflow_type,
                language=language,
                category=None,
                guidance_key=None,
                source_feature_id=None,
                source_feature_key=None,
                reason=omission_reason,
                detail=detail,
                scope=None,
                confidence=None,
                profile_status=profile.status if profile else None,
                evidence_item_count=None,
            ),
        )
        guidance_version = self.GUIDANCE_VERSION
        profile_fingerprint = profile.fingerprint if profile else None
        profile_version = profile.profile_version if profile else None
        profile_status = profile.status if profile else None
        rendered_guidance = self._render_bundle((), language=language, profile_status=profile_status)
        bundle_fingerprint = _stable_id(
            {
                "guidance_version": guidance_version.value,
                "profile_fingerprint": profile_fingerprint,
                "profile_status": profile_status.value if profile_status else None,
                "creator_id": request.creator_id,
                "project_id": request.project_id,
                "workflow_type": request.workflow_type,
                "language": language,
                "enabled": request.enabled,
                "budget_requested": {"max_items": max(0, int(request.max_items)), "max_characters": max(0, int(request.max_characters))},
                "guidance_item_ids": [],
                "omitted_item_ids": [item.id for item in omitted],
                "conflict_ids": [],
            }
        )
        return CreatorVoiceGuidanceBundle(
            creator_id=request.creator_id,
            project_id=request.project_id,
            workflow_type=request.workflow_type,
            language=language,
            guidance_version=guidance_version,
            profile_fingerprint=profile_fingerprint,
            profile_version=profile_version,
            profile_status=profile_status,
            guidance_state=guidance_state,
            guidance_items=(),
            omitted_items=omitted,
            conflicts=(),
            warnings=(detail,),
            budget_requested={"max_items": max(0, int(request.max_items)), "max_characters": max(0, int(request.max_characters))},
            budget_used={"max_items": 0, "max_characters": len(rendered_guidance)},
            rendered_guidance=rendered_guidance,
            request_trace={
                "enabled": request.enabled,
                "profile_status": profile_status.value if profile_status else None,
                "profile_fingerprint": profile_fingerprint,
                "omission_reason": omission_reason.value,
                "omission_detail": detail,
            },
            bundle_fingerprint=bundle_fingerprint,
            created_at=utc_now(),
        )

    def _normalize_request(self, request: CreatorVoiceGuidanceRequest | dict[str, object]) -> CreatorVoiceGuidanceRequest:
        if isinstance(request, CreatorVoiceGuidanceRequest):
            return request
        if not isinstance(request, dict):
            raise TypeError("request must be a CreatorVoiceGuidanceRequest or dict.")
        profile = request.get("profile")
        return CreatorVoiceGuidanceRequest(
            creator_id=str(request.get("creator_id") or ""),
            project_id=request.get("project_id") if request.get("project_id") is not None else None,
            workflow_type=str(request.get("workflow_type") or ""),
            language=request.get("language") if request.get("language") is not None else None,
            current_user_instruction=request.get("current_user_instruction") if request.get("current_user_instruction") is not None else None,
            project_instruction=request.get("project_instruction") if request.get("project_instruction") is not None else None,
            profile=profile,
            enabled=bool(request.get("enabled", True)),
            max_items=int(request.get("max_items", self.MAX_ITEMS)),
            max_characters=int(request.get("max_characters", self.MAX_CHARACTERS)),
        )

    def render_guidance(self, bundle: CreatorVoiceGuidanceBundle) -> str:
        return bundle.rendered_guidance

    def diagnostics(self, request: CreatorVoiceGuidanceRequest | dict[str, object], *, debug: bool = False) -> dict[str, object]:
        bundle = self.build_guidance(request)
        payload = bundle.to_dict()
        if not debug:
            payload["request_trace"] = dict(payload["request_trace"])
        return {
            "bundle": payload,
            "summary": {
                "creator_id": bundle.creator_id,
                "project_id": bundle.project_id,
                "workflow_type": bundle.workflow_type,
                "language": bundle.language,
                "guidance_state": bundle.guidance_state.value,
                "profile_status": bundle.profile_status.value if bundle.profile_status else None,
                "guidance_count": len(bundle.guidance_items),
                "omitted_count": len(bundle.omitted_items),
                "conflict_count": len(bundle.conflicts),
                "bundle_fingerprint": bundle.bundle_fingerprint,
            },
        }


def build_creator_voice_guidance_service(*, logger: logging.Logger | None = None) -> CreatorVoiceGuidanceService:
    return CreatorVoiceGuidanceService(logger=logger)
