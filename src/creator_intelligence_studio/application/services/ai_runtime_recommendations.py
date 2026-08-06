"""Guided model recommendation helpers for AI runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIModelCatalogEntry, AIRoleAssignment


CURATED_MODEL_CATALOG_VERSION = "v31-curated-2026-08-01"


@dataclass(frozen=True, slots=True)
class CompatibilityRule:
    provider: str
    model_id_patterns: tuple[str, ...]
    roles: tuple[str, ...]
    allowed_modalities: tuple[str, ...] = ("text",)
    required_capabilities: tuple[str, ...] = ()
    blocked_tokens: tuple[str, ...] = ()
    stability: str = "provisional"
    priority: int = 50
    confidence: str = "provisional"
    source: str = "curated_seed"
    effective_at: str = "2026-08-01"
    reviewed_at: str = "2026-08-01"
    notes: tuple[str, ...] = ()

    def matches(self, model: AIModelCatalogEntry) -> bool:
        if model.provider != self.provider:
            return False
        for pattern in self.model_id_patterns:
            if re.search(pattern, model.model_id, flags=re.IGNORECASE):
                return True
        return False


@dataclass(frozen=True, slots=True)
class ProfileDefinition:
    key: str
    label: str
    description: str
    relative_cost_label: str
    quality_bias: str


@dataclass(frozen=True, slots=True)
class ModelRecommendation:
    role: str
    role_label: str
    required_now: bool
    proposed_model: dict[str, Any] | None
    alternatives: tuple[dict[str, Any], ...]
    confidence: str
    reason: str
    warnings: tuple[str, ...]
    recommendation_tag: str
    compatibility_state: str
    evaluation_state: str
    availability_state: str
    source: str
    profile_key: str
    profile_label: str
    relative_cost_label: str
    current_assignment: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "role_label": self.role_label,
            "required_now": self.required_now,
            "proposed_model": self.proposed_model,
            "alternatives": list(self.alternatives),
            "confidence": self.confidence,
            "reason": self.reason,
            "warnings": list(self.warnings),
            "recommendation_tag": self.recommendation_tag,
            "compatibility_state": self.compatibility_state,
            "evaluation_state": self.evaluation_state,
            "availability_state": self.availability_state,
            "source": self.source,
            "profile_key": self.profile_key,
            "profile_label": self.profile_label,
            "relative_cost_label": self.relative_cost_label,
            "current_assignment": self.current_assignment,
        }


@dataclass(frozen=True, slots=True)
class GuidedConfigurationSummary:
    provider: str
    provider_label: str
    profile_key: str
    profile_label: str
    profile_description: str
    catalog_version: str
    synchronized_at: str | None
    found_count: int
    compatible_count: int
    unknown_count: int
    recommended_count: int
    availability_state: str
    compatibility_state: str
    relative_cost_label: str
    warnings: tuple[str, ...]
    roles: tuple[ModelRecommendation, ...]
    current_assignment_warning: str | None = None
    first_setup_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_label": self.provider_label,
            "profile_key": self.profile_key,
            "profile_label": self.profile_label,
            "profile_description": self.profile_description,
            "catalog_version": self.catalog_version,
            "synchronized_at": self.synchronized_at,
            "found_count": self.found_count,
            "compatible_count": self.compatible_count,
            "unknown_count": self.unknown_count,
            "recommended_count": self.recommended_count,
            "availability_state": self.availability_state,
            "compatibility_state": self.compatibility_state,
            "relative_cost_label": self.relative_cost_label,
            "warnings": list(self.warnings),
            "roles": [role.to_dict() for role in self.roles],
            "current_assignment_warning": self.current_assignment_warning,
            "first_setup_message": self.first_setup_message,
        }


ROLE_LABELS = {
    "cheap_structured_model": "Modelo estructurado economico",
    "general_reasoning_model": "Modelo de razonamiento general",
    "creative_writing_model": "Modelo de escritura creativa",
    "multimodal_model": "Modelo multimodal",
    "transcription_fallback_model": "Modelo de respaldo para transcripcion",
    "evaluation_model": "Modelo de evaluacion",
}


PROFILE_DEFINITIONS: dict[str, ProfileDefinition] = {
    "economico": ProfileDefinition(
        key="economico",
        label="Económico",
        description="Prioriza el menor costo y modelos pequeños para tareas estructuradas.",
        relative_cost_label="Bajo",
        quality_bias="cost",
    ),
    "equilibrado": ProfileDefinition(
        key="equilibrado",
        label="Equilibrado",
        description="Balance de costo, estabilidad y calidad. Es el perfil predeterminado.",
        relative_cost_label="Medio",
        quality_bias="balanced",
    ),
    "maxima_calidad": ProfileDefinition(
        key="maxima_calidad",
        label="Máxima calidad",
        description="Prioriza capacidad y estabilidad, con advertencia de mayor costo.",
        relative_cost_label="Alto",
        quality_bias="quality",
    ),
    "personalizado": ProfileDefinition(
        key="personalizado",
        label="Personalizado",
        description="Abre el modo avanzado de asignación manual.",
        relative_cost_label="Variable",
        quality_bias="manual",
    ),
}


ROLE_REQUIRED_NOW = {
    "cheap_structured_model": True,
    "general_reasoning_model": False,
    "creative_writing_model": False,
    "multimodal_model": False,
    "transcription_fallback_model": False,
    "evaluation_model": False,
}


CURATED_COMPATIBILITY_MATRIX: dict[str, tuple[CompatibilityRule, ...]] = {
    "openai": (
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-4\.1-mini$", r"^gpt-4o-mini$"),
            roles=("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model"),
            allowed_modalities=("text",),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=100,
            confidence="approved",
            source="https://developers.openai.com/api/docs/models/gpt-4o-mini",
            notes=("Small text-first OpenAI models are preferred for structured work.",),
        ),
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-4\.1$", r"^gpt-4o$"),
            roles=("general_reasoning_model", "creative_writing_model", "evaluation_model", "cheap_structured_model"),
            allowed_modalities=("text",),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=80,
            confidence="approved",
            source="https://developers.openai.com/api/docs/models/gpt-4.1",
            notes=("Larger OpenAI chat models are preferred when quality matters more than cost.",),
        ),
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-4o-mini$",),
            roles=("multimodal_model",),
            allowed_modalities=("text", "image"),
            required_capabilities=("structured_output", "image_input"),
            stability="approved",
            priority=95,
            confidence="approved",
            source="https://developers.openai.com/api/docs/models/gpt-4o-mini",
            notes=("Known multimodal family for OpenAI.",),
        ),
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-5\.6-(sol|terra|luna)$", r"^gpt-5\.6-(sol|terra|luna)-\d{4}-\d{2}-\d{2}$"),
            roles=("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model"),
            allowed_modalities=("text", "image"),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=110,
            confidence="approved",
            source="https://developers.openai.com/api/docs/models/gpt-5.6-luna",
            notes=("GPT-5.6 family model for cost-sensitive or balanced workloads.",),
        ),
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-5-mini$", r"^gpt-5-mini-\d{4}-\d{2}-\d{2}$", r"^gpt-5$", r"^gpt-5-\d{4}-\d{2}-\d{2}$"),
            roles=("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model"),
            allowed_modalities=("text", "image"),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=105,
            confidence="approved",
            source="https://developers.openai.com/api/docs/models/gpt-5-mini",
            notes=("Near-frontier model for cost-sensitive, low-latency, high-volume workloads.",),
        ),
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-5\.1$", r"^gpt-5\.1-\d{4}-\d{2}-\d{2}$"),
            roles=("general_reasoning_model", "creative_writing_model", "evaluation_model"),
            allowed_modalities=("text", "image"),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=100,
            confidence="approved",
            source="https://developers.openai.com/api/docs/models/gpt-5.1",
            notes=("Flagship model for coding and agentic tasks with configurable reasoning effort.",),
        ),
        CompatibilityRule(
            provider="openai",
            model_id_patterns=(r"^gpt-3\.5-turbo$",),
            roles=("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model"),
            allowed_modalities=("text",),
            required_capabilities=("structured_output",),
            stability="deprecated",
            priority=5,
            confidence="rejected",
            source="https://platform.openai.com/docs/api-reference/models/object?lang=curl",
            notes=("Legacy assignment should remain visible but not recommended.",),
        ),
    ),
    "anthropic": (
        CompatibilityRule(
            provider="anthropic",
            model_id_patterns=(r"^claude-4", r"^claude-3\.5"),
            roles=("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model", "multimodal_model"),
            allowed_modalities=("text", "image"),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=100,
            confidence="approved",
            notes=("Primary Anthropic family for reasoning and writing.",),
        ),
        CompatibilityRule(
            provider="anthropic",
            model_id_patterns=(r"^claude-3",),
            roles=("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model"),
            allowed_modalities=("text", "image"),
            required_capabilities=("structured_output",),
            stability="approved",
            priority=80,
            confidence="provisional",
            notes=("Older Claude models remain usable when verified by the account.",),
        ),
    ),
}


def get_profile_definition(profile_key: str) -> ProfileDefinition:
    return PROFILE_DEFINITIONS.get(profile_key, PROFILE_DEFINITIONS["equilibrado"])


def _text_haystack(model: AIModelCatalogEntry) -> str:
    capabilities = model.capabilities_json if isinstance(model.capabilities_json, dict) else {}
    capability_values: list[str] = []
    for key, value in capabilities.items():
        if isinstance(value, bool):
            if value:
                capability_values.append(str(key))
        elif isinstance(value, (str, int, float)):
            capability_values.append(str(value))
        elif isinstance(value, dict):
            capability_values.extend(str(inner) for inner in value.values() if inner is not None)
        elif isinstance(value, (list, tuple, set)):
            capability_values.extend(str(inner) for inner in value if inner is not None)
    return " ".join(
        part
        for part in (
            model.provider,
            model.model_id,
            model.display_name,
            model.snapshot_or_version or "",
            model.replacement_model_id or "",
            " ".join(capability_values),
        )
    ).lower()


def _tokens(model: AIModelCatalogEntry) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _text_haystack(model)) if token}


def _role_blocked_tokens(role: str) -> tuple[str, ...]:
    blocked = {
        "cheap_structured_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "general_reasoning_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "creative_writing_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "multimodal_model": ("transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "transcription_fallback_model": ("tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "evaluation_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
    }
    return blocked.get(role, ())


def _preview_like(model: AIModelCatalogEntry, tokens: set[str]) -> bool:
    return "preview" in tokens


def _snapshot_like(model: AIModelCatalogEntry, tokens: set[str]) -> bool:
    if model.snapshot_or_version:
        return True
    return any(token.isdigit() and len(token) >= 4 for token in tokens)


def _known_role_rule(provider: str, model: AIModelCatalogEntry, role: str) -> CompatibilityRule | None:
    for rule in CURATED_COMPATIBILITY_MATRIX.get(provider, ()):  # pragma: no branch - tiny tuple
        if rule.matches(model) and role in rule.roles:
            return rule
    return None


def classify_model_for_role(model: AIModelCatalogEntry, role: str) -> dict[str, Any]:
    tokens = _tokens(model)
    if model.status == "blocked":
        return {
            "compatibility_state": "incompatible_confirmed",
            "availability_state": "blocked",
            "evaluation_state": "rejected",
            "recommendation_tag": "Incompatible confirmado",
            "reason": "El modelo esta bloqueado.",
            "warnings": ("El modelo esta bloqueado.",),
            "is_visible_by_default": False,
        }
    if model.status == "unavailable":
        return {
            "compatibility_state": "incompatible_confirmed",
            "availability_state": "unavailable",
            "evaluation_state": "rejected",
            "recommendation_tag": "Incompatible confirmado",
            "reason": "El modelo no esta disponible.",
            "warnings": ("El modelo no esta disponible.",),
            "is_visible_by_default": False,
        }
    if model.status == "deprecated":
        return {
            "compatibility_state": "incompatible_confirmed",
            "availability_state": "deprecated",
            "evaluation_state": "rejected",
            "recommendation_tag": "Incompatible confirmado",
            "reason": "El modelo esta deprecado.",
            "warnings": ("El modelo esta deprecado.",),
            "is_visible_by_default": False,
        }

    blocked_tokens = _role_blocked_tokens(role)
    if any(any(token.startswith(prefix) for token in tokens) for prefix in blocked_tokens):
        return {
            "compatibility_state": "incompatible_confirmed",
            "availability_state": "available",
            "evaluation_state": "rejected",
            "recommendation_tag": "Incompatible confirmado",
            "reason": "Modelo especializado incompatible con este rol.",
            "warnings": ("Modelo especializado incompatible con este rol.",),
            "is_visible_by_default": False,
        }

    rule = _known_role_rule(model.provider, model, role)
    capabilities = model.capabilities_json if isinstance(model.capabilities_json, dict) else {}
    explicit_image = capabilities.get("image_input")
    explicit_audio = capabilities.get("audio_input")
    explicit_structured = capabilities.get("structured_output")

    if role == "multimodal_model" and explicit_image is False:
        return {
            "compatibility_state": "incompatible_confirmed",
            "availability_state": "available",
            "evaluation_state": "rejected",
            "recommendation_tag": "Incompatible confirmado",
            "reason": "El modelo no confirma entrada de imagen.",
            "warnings": ("El modelo no confirma entrada de imagen.",),
            "is_visible_by_default": False,
        }
    if role == "transcription_fallback_model" and explicit_audio is False:
        return {
            "compatibility_state": "incompatible_confirmed",
            "availability_state": "available",
            "evaluation_state": "rejected",
            "recommendation_tag": "Incompatible confirmado",
            "reason": "El modelo no confirma entrada de audio.",
            "warnings": ("El modelo no confirma entrada de audio.",),
            "is_visible_by_default": False,
        }

    if _preview_like(model, tokens):
        return {
            "compatibility_state": "compatibility_unknown",
            "availability_state": "available",
            "evaluation_state": "unreviewed",
            "recommendation_tag": "No evaluado",
            "reason": "Variante preview o experimental.",
            "warnings": ("Variante preview o experimental.",),
            "is_visible_by_default": False,
        }
    if _snapshot_like(model, tokens):
        return {
            "compatibility_state": "compatibility_unknown",
            "availability_state": "available",
            "evaluation_state": "unreviewed",
            "recommendation_tag": "No evaluado",
            "reason": "Variante snapshot o tecnica sin matriz curada.",
            "warnings": ("Variante snapshot o tecnica sin matriz curada.",),
            "is_visible_by_default": False,
        }

    if rule is not None:
        confidence = "compatible_verified_catalog" if rule.confidence == "approved" and model.status == "approved" else "compatible_by_verified_catalog"
        recommendation_tag = "Compatible verificado" if confidence == "compatible_verified_catalog" else "Compatible pendiente de benchmark"
        warnings = tuple(rule.notes)
        reason = "Modelo reconocido por la matriz curada."
        if rule.stability == "deprecated":
            confidence = "incompatible_confirmed"
            recommendation_tag = "Incompatible confirmado"
            reason = "El catalogo curado lo marca como legado o deprecado."
            warnings = warnings + ("Asociacion antigua conservada, pero no recomendada.",)
        return {
            "compatibility_state": confidence,
            "availability_state": "available",
            "evaluation_state": "approved" if confidence == "compatible_verified_catalog" else "provisional",
            "recommendation_tag": recommendation_tag,
            "reason": reason,
            "warnings": warnings,
            "is_visible_by_default": not _preview_like(model, tokens) and confidence != "incompatible_confirmed",
            "priority": rule.priority,
            "source": rule.source,
        }

    if role == "multimodal_model" and explicit_image is True:
        return {
            "compatibility_state": "compatible_by_verified_catalog",
            "availability_state": "available",
            "evaluation_state": "provisional",
            "recommendation_tag": "Compatible verificado",
            "reason": "Entrada de imagen confirmada por el catalogo.",
            "warnings": (),
            "is_visible_by_default": not _preview_like(model, tokens),
        }
    if role == "transcription_fallback_model" and explicit_audio is True:
        return {
            "compatibility_state": "compatible_by_verified_catalog",
            "availability_state": "available",
            "evaluation_state": "provisional",
            "recommendation_tag": "Compatible verificado",
            "reason": "Entrada de audio confirmada por el catalogo.",
            "warnings": (),
            "is_visible_by_default": not _preview_like(model, tokens),
        }

    if role == "cheap_structured_model" and explicit_structured is True:
        return {
            "compatibility_state": "compatible_by_verified_catalog",
            "availability_state": "available",
            "evaluation_state": "tested" if model.status == "testing" else "approved",
            "recommendation_tag": "Compatible verificado",
            "reason": "Modelo utilizable para tareas estructuradas.",
            "warnings": (),
            "is_visible_by_default": not _preview_like(model, tokens),
        }

    if model.status == "testing":
        return {
            "compatibility_state": "compatibility_unknown",
            "availability_state": "available",
            "evaluation_state": "tested",
            "recommendation_tag": "Compatible pendiente de benchmark",
            "reason": "Modelo disponible en la cuenta, pero todavia no evaluado por Creator Intelligence Studio.",
            "warnings": ("Modelo disponible en la cuenta, pero todavia no evaluado por Creator Intelligence Studio.",),
            "is_visible_by_default": True,
            "priority": 0,
            "source": "provider_catalog",
        }

    return {
        "compatibility_state": "compatibility_unknown",
        "availability_state": "available",
        "evaluation_state": "unreviewed",
        "recommendation_tag": "No evaluado",
        "reason": "Modelo disponible en la cuenta, pero todavia no evaluado por Creator Intelligence Studio.",
        "warnings": ("Modelo disponible en la cuenta, pero todavia no evaluado por Creator Intelligence Studio.",),
        "is_visible_by_default": True,
        "priority": 0,
        "source": "provider_catalog",
    }


class RecommendedModelResolver:
    def __init__(self, *, curated_matrix_version: str = CURATED_MODEL_CATALOG_VERSION) -> None:
        self.curated_matrix_version = curated_matrix_version

    def _price_value(self, model: AIModelCatalogEntry) -> float:
        values = [value for value in (model.input_price_per_million, model.output_price_per_million) if value is not None]
        if not values:
            return 1_000_000.0
        return float(sum(values))

    def _size_score(self, model: AIModelCatalogEntry) -> int:
        text = f"{model.model_id} {model.display_name}".lower()
        score = 0
        if any(token in text for token in ("mini", "small", "nano", "lite")):
            score -= 3
        if any(token in text for token in ("large", "pro", "max", "opus")):
            score += 3
        if "sonnet" in text:
            score += 2
        if "4.1" in text or "4o" in text:
            score += 1
        return score

    def _profile_bonus(self, model: AIModelCatalogEntry, profile_key: str) -> int:
        text = f"{model.model_id} {model.display_name}".lower()
        if profile_key == "economico":
            return -self._size_score(model)
        if profile_key == "maxima_calidad":
            return self._size_score(model) + (2 if model.status == "approved" else 0)
        return 0

    def _availability_rank(self, model: AIModelCatalogEntry) -> int:
        return {"approved": 3, "testing": 2, "deprecated": 1, "unavailable": 0, "blocked": 0}.get(model.status, 0)

    def _model_sort_key(self, model: AIModelCatalogEntry, classification: dict[str, Any], profile_key: str) -> tuple[int, int, float, int, str, str]:
        compatibility_order = {
            "compatible_verified_catalog": 0,
            "compatible_by_verified_catalog": 1,
            "compatibility_unknown": 2,
            "incompatible_confirmed": 3,
        }.get(str(classification.get("compatibility_state")), 4)
        rule_priority = int(classification.get("priority") or 0)
        recommendation_order = {
            "Compatible verificado": 0,
            "Compatible pendiente de benchmark": 1,
            "No evaluado": 2,
            "Incompatible confirmado": 3,
        }.get(str(classification.get("recommendation_tag")), 4)
        return (
            compatibility_order,
            -rule_priority,
            self._price_value(model) - self._profile_bonus(model, profile_key),
            -self._availability_rank(model),
            str(recommendation_order),
            model.display_name.lower(),
            model.model_id.lower(),
        )

    def _current_assignment_for_role(
        self,
        role: str,
        assignments: list[AIRoleAssignment] | None,
        provider: str,
    ) -> AIRoleAssignment | None:
        if not assignments:
            return None
        for assignment in assignments:
            if assignment.role == role and assignment.provider == provider and assignment.is_enabled:
                return assignment
        return None

    def _available_models(self, models: list[AIModelCatalogEntry], role: str) -> list[AIModelCatalogEntry]:
        return [
            model
            for model in models
            if model.status not in {"blocked", "unavailable", "deprecated"}
            and not any(token in _text_haystack(model) for token in _role_blocked_tokens(role))
        ]

    def recommend_role(
        self,
        *,
        provider: str,
        role: str,
        catalog: list[AIModelCatalogEntry],
        profile_key: str = "equilibrado",
        assignments: list[AIRoleAssignment] | None = None,
    ) -> ModelRecommendation:
        profile = get_profile_definition(profile_key)
        role_label = ROLE_LABELS.get(role, role)
        current_assignment = self._current_assignment_for_role(role, assignments, provider)
        current_assignment_dict = current_assignment.to_dict() if current_assignment else None
        candidates = self._available_models(catalog, role)
        classified: list[tuple[AIModelCatalogEntry, dict[str, Any]]] = []
        verified_classified: list[tuple[AIModelCatalogEntry, dict[str, Any]]] = []
        unknown_count = 0
        confirmed_count = 0
        for model in candidates:
            classification = classify_model_for_role(model, role)
            if classification["compatibility_state"] in {"compatible_confirmed", "compatible_verified_catalog", "compatible_by_verified_catalog"}:
                confirmed_count += 1
                verified_classified.append((model, classification))
            if classification["compatibility_state"] == "compatibility_unknown":
                unknown_count += 1
            if classification["compatibility_state"] != "incompatible_confirmed":
                classified.append((model, classification))
        if not verified_classified:
            reason = "No hay un modelo verificado para este rol."
            if current_assignment_dict is not None:
                reason = "La asignacion actual no esta recomendada para la matriz curada."
            return ModelRecommendation(
                role=role,
                role_label=role_label,
                required_now=ROLE_REQUIRED_NOW.get(role, False),
                proposed_model=None,
                alternatives=(),
                confidence="low",
                reason=reason,
                warnings=("No hay un modelo recomendado disponible.",),
                recommendation_tag="No evaluado",
                compatibility_state="compatibility_unknown",
                evaluation_state="unreviewed",
                availability_state="available",
                source="curated_matrix",
                profile_key=profile.key,
                profile_label=profile.label,
                relative_cost_label=profile.relative_cost_label,
                current_assignment=current_assignment_dict,
            )

        verified_classified.sort(key=lambda pair: self._model_sort_key(pair[0], pair[1], profile.key))
        best_model, best_classification = verified_classified[0]
        alternatives = tuple(model.to_dict() for model, _classification in verified_classified[1:4])
        confidence = "high" if best_classification["compatibility_state"] == "compatible_verified_catalog" else "medium"
        if best_classification["compatibility_state"] == "compatibility_unknown":
            confidence = "low"
        reason = str(best_classification.get("reason") or "Modelo recomendado por la matriz curada.")
        warnings = tuple(best_classification.get("warnings") or ())
        if current_assignment_dict and current_assignment_dict.get("model_catalog_id") != (best_model.id or best_model.model_id):
            warnings = warnings + ("Esta asignacion no esta recomendada.",)
        return ModelRecommendation(
            role=role,
            role_label=role_label,
            required_now=ROLE_REQUIRED_NOW.get(role, False),
            proposed_model=best_model.to_dict(),
            alternatives=alternatives,
            confidence=confidence,
            reason=reason,
            warnings=warnings,
            recommendation_tag=str(best_classification.get("recommendation_tag") or "Compatible pendiente de benchmark"),
            compatibility_state=str(best_classification.get("compatibility_state") or "compatibility_unknown"),
            evaluation_state=str(best_classification.get("evaluation_state") or "unreviewed"),
            availability_state=str(best_classification.get("availability_state") or "available"),
            source=str(best_classification.get("source") or ("curated_matrix" if any(rule.matches(best_model) for rule in CURATED_COMPATIBILITY_MATRIX.get(provider, ())) else "provider_catalog")),
            profile_key=profile.key,
            profile_label=profile.label,
            relative_cost_label=profile.relative_cost_label,
            current_assignment=current_assignment_dict,
        )

    def summarize_provider(
        self,
        *,
        provider: str,
        catalog: list[AIModelCatalogEntry],
        assignments: list[AIRoleAssignment] | None = None,
        profile_key: str = "equilibrado",
        synchronized_at: str | None = None,
    ) -> GuidedConfigurationSummary:
        profile = get_profile_definition(profile_key)
        roles: list[ModelRecommendation] = []
        confirmed_count = 0
        unknown_count = 0
        warnings: list[str] = []
        for role in ROLE_LABELS:
            recommendation = self.recommend_role(
                provider=provider,
                role=role,
                catalog=catalog,
                profile_key=profile.key,
                assignments=assignments,
            )
            roles.append(recommendation)
            if recommendation.compatibility_state in {"compatible_confirmed", "compatible_verified_catalog", "compatible_by_verified_catalog"}:
                confirmed_count += 1
            if recommendation.compatibility_state == "compatibility_unknown":
                unknown_count += 1
            warnings.extend(recommendation.warnings)
        current_warning = None
        if any(role.current_assignment for role in roles):
            for role in roles:
                if role.current_assignment and role.proposed_model and role.current_assignment.get("model_catalog_id") != role.proposed_model.get("id"):
                    current_warning = "Esta asignacion no esta recomendada."
                    break
        first_setup_message = None
        if not any(role.current_assignment for role in roles if role.required_now):
            first_setup_message = "Encontramos modelos disponibles. Puedes aplicar la configuracion equilibrada recomendada."
        availability_state = "available" if catalog else "unavailable"
        compatibility_state = "verified" if confirmed_count else "partial" if unknown_count else "unknown"
        return GuidedConfigurationSummary(
            provider=provider,
            provider_label=provider.title(),
            profile_key=profile.key,
            profile_label=profile.label,
            profile_description=profile.description,
            catalog_version=self.curated_matrix_version,
            synchronized_at=synchronized_at,
            found_count=len(catalog),
            compatible_count=confirmed_count,
            unknown_count=unknown_count,
            recommended_count=sum(1 for role in roles if role.proposed_model is not None),
            availability_state=availability_state,
            compatibility_state=compatibility_state,
            relative_cost_label=profile.relative_cost_label,
            warnings=tuple(dict.fromkeys(warnings)),
            roles=tuple(roles),
            current_assignment_warning=current_warning,
            first_setup_message=first_setup_message,
        )
