"""Application service for AI runtime orchestration."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from creator_intelligence_studio.infrastructure.ai_runtime import (
    AIBudgetPolicy,
    AICache,
    AIExecutionCacheInfo,
    AICostSummary,
    AIExecutionRequest,
    AIExecutionRecord,
    AIExecutionResult,
    AIExecutionLatency,
    AIExecutionError,
    AIExecutionPayload,
    AIExecutionUsage,
    AIModelCatalogEntry,
    AIExecutionValidation,
    AIProviderDiagnostic,
    AIProviderModelSyncReport,
    AIPromptTemplate,
    AIRoleAssignment,
    AIRuntimeSetting,
    AnthropicProvider,
    BudgetPolicy,
    CredentialStore,
    CostEstimator,
    CostTracker,
    ModelRegistry,
    OpenAIProvider,
    PrivacyPolicyEngine,
    PromptRegistry,
    SQLiteAIRuntimeRepository,
    AIOrchestrator,
    AIResultValidator,
)
from creator_intelligence_studio.application.services.ai_runtime_recommendations import (
    RecommendedModelResolver,
    classify_model_for_role,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class AIRuntimeStatus:
    ai_runtime_available: bool
    openai_configured: bool
    anthropic_configured: bool
    model_roles_configured: bool
    budget_policy_configured: bool
    credential_store_available: bool


class AIRuntimeService:
    ROLE_REQUIREMENTS: dict[str, dict[str, bool]] = {
        "cheap_structured_model": {"structured_output": True},
        "general_reasoning_model": {"structured_output": True},
        "creative_writing_model": {"structured_output": True},
        "multimodal_model": {"structured_output": True, "image_input": True},
        "transcription_fallback_model": {"audio_input": True},
        "evaluation_model": {"structured_output": True},
    }
    ROLE_BLOCKED_KEYWORDS: dict[str, tuple[str, ...]] = {
        "cheap_structured_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "general_reasoning_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "creative_writing_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "multimodal_model": ("transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "transcription_fallback_model": ("tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
        "evaluation_model": ("audio", "transcrib", "tts", "search", "codex", "embed", "moderation", "realtime", "legacy"),
    }

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        database: SQLiteDatabase,
        credential_store: CredentialStore,
        repository: SQLiteAIRuntimeRepository,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.database = database
        self.credential_store = credential_store
        self.repository = repository
        self.model_registry = ModelRegistry(repository)
        self.prompt_registry = PromptRegistry(repository)
        self.cache = AICache(repository)
        self.recommended_model_resolver = RecommendedModelResolver()
        self.providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
        }
        self.orchestrator = AIOrchestrator(
            model_registry=self.model_registry,
            prompt_registry=self.prompt_registry,
            credential_store=self.credential_store,
            repository=self.repository,
            providers=self.providers,
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
            cache=self.cache,
        )
        self._seed_runtime()

    def _seed_runtime(self) -> None:
        existing = self.prompt_registry.get_approved("provider_diagnostic")
        if existing is None:
            self.prompt_registry.ensure_template(
                AIPromptTemplate(
                    template_key="provider_diagnostic",
                    task_type="provider_diagnostic",
                    operation="extract",
                    version=1,
                    status="approved",
                    required_capabilities_json={"structured_output": True},
                    instruction_layers_json={
                        "layers": [
                            "Return only JSON.",
                            "Keep the response minimal.",
                            "Do not reference creator data.",
                        ]
                    },
                    input_schema_json={
                        "type": "object",
                        "properties": {
                            "short_message": {"type": "string"},
                        },
                    },
                    output_schema_json={
                        "type": "object",
                        "required": ["status", "logical_role", "short_message"],
                        "properties": {
                            "status": {"const": "ok"},
                            "logical_role": {"type": "string"},
                            "short_message": {"type": "string"},
                        },
                    },
                    validation_profile_json={
                        "required_keys": ["status", "logical_role", "short_message"]
                    },
                    change_notes="Initial diagnostic template.",
                    approved_at=self._now(),
                    created_at=self._now(),
                    updated_at=self._now(),
                )
            )
        default_budget = self.repository.get_budget_policy(None, None)
        if default_budget is None:
            self.repository.upsert_budget_policy(
                AIBudgetPolicy(
                    monthly_limit=None,
                    per_task_limit=None,
                    hard_block_enabled=True,
                    currency="USD",
                    effective_from=self._now(),
                    created_at=self._now(),
                    updated_at=self._now(),
                )
            )
        self._ensure_runtime_flags()

    def _ensure_runtime_flags(self) -> None:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="provider_enabled",
                setting_value_json={"openai": True, "anthropic": True},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="env_credentials_enabled",
                setting_value_json={"enabled": os.environ.get("CIS_ENABLE_ENV_CREDENTIALS") == "1"},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="cross_provider_fallback_enabled",
                setting_value_json={"enabled": True},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="cost_approval_threshold",
                setting_value_json={"value": 0.90},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def _runtime_setting_value(self, setting_key: str, scope_id: str | None = None) -> dict[str, Any] | None:
        setting = self.repository.get_runtime_setting("application" if scope_id is None else "provider", setting_key, scope_id)
        if setting is None:
            return None
        return setting.setting_value_json

    def get_runtime_setting(self, setting_key: str, scope_id: str | None = None) -> dict[str, Any] | None:
        return self._runtime_setting_value(setting_key, scope_id)

    def set_runtime_setting(self, setting_key: str, value: dict[str, Any], scope_id: str | None = None) -> dict[str, Any]:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application" if scope_id is None else "provider",
                scope_id=scope_id,
                setting_key=setting_key,
                setting_value_json=value,
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        return value

    def _runtime_flag(self, setting_key: str, *, scope_id: str | None = None, default: bool = False) -> bool:
        value = self._runtime_setting_value(setting_key, scope_id)
        if isinstance(value, dict):
            if scope_id is None:
                enabled = value.get("enabled")
                if enabled is None:
                    return default
                return bool(enabled)
            enabled = value.get("value")
            if enabled is None:
                enabled = value.get("enabled")
            if enabled is None:
                return default
            return bool(enabled)
        return default

    def _runtime_number(self, setting_key: str, *, scope_id: str | None = None, default: float | None = None) -> float | None:
        value = self._runtime_setting_value(setting_key, scope_id)
        if isinstance(value, dict):
            raw = value.get("value")
            if raw is None:
                raw = value.get("threshold")
            if raw is None:
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default
        return default

    def _record_provider_check(self, provider: str, diagnostic: AIProviderDiagnostic) -> None:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="provider",
                scope_id=provider,
                setting_key="last_check",
                setting_value_json={
                    "provider": provider,
                    "status": diagnostic.status,
                    "message": diagnostic.message,
                    "configured": diagnostic.configured,
                    "model_id": diagnostic.model_id,
                    "latency_ms": diagnostic.latency_ms,
                    "usage": diagnostic.usage,
                    "cost": diagnostic.cost,
                    "error": diagnostic.error,
                    "checked_at": self._now(),
                },
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _execution_to_request(self, execution: AIExecutionRecord) -> AIExecutionRequest:
        summary = execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}
        metadata = summary.get("metadata") if isinstance(summary.get("metadata"), dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        return AIExecutionRequest(
            request_id=str(summary.get("request_id") or f"{execution.execution_uuid}:retry"),
            task_type=execution.task_type,
            operation=execution.operation,
            creator_id=execution.creator_id,
            project_id=execution.project_id,
            model_role=execution.requested_model_role,
            quality_level=execution.quality_level,
            privacy_class=execution.privacy_class,
            input_data={
                "status": "ok",
                "logical_role": execution.requested_model_role or "cheap_structured_model",
                "short_message": "Provider diagnostic request.",
            },
            context_package={},
            output_contract={"required": ["status", "logical_role", "short_message"]},
            budget=dict(summary.get("budget") or {}),
            cache_policy=str(summary.get("cache_policy") or "use"),
            fallback_policy=str(summary.get("fallback_policy") or "none"),
            approval_policy="not_required",
            metadata=dict(metadata),
        )

    def _approval_payload(self, *, execution: AIExecutionRecord, approved: bool, actor: str | None, reason: str | None, now: str) -> dict[str, object]:
        summary = execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}
        approval_summary = summary.get("approval_summary") if isinstance(summary.get("approval_summary"), dict) else {}
        payload: dict[str, object] = {
            "execution_id": execution.execution_uuid,
            "decision": "approved" if approved else "rejected",
            "actor": actor,
            "reason": reason,
            "approved_at": now if approved else None,
            "rejected_at": now if not approved else None,
            "provider_at_decision": execution.provider,
            "model_at_decision": execution.model_catalog_id,
            "role_at_decision": execution.requested_model_role,
            "scope": approval_summary.get("scope") or "single_execution",
            "estimated_cost_at_decision": approval_summary.get("estimated_cost_at_approval"),
            "approval_summary": approval_summary,
        }
        return payload

    def _approval_metadata(self, execution: AIExecutionRecord) -> dict[str, object] | None:
        summary = execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}
        approval_summary = summary.get("approval_summary")
        if isinstance(approval_summary, dict):
            return approval_summary
        if summary.get("approval_state") == "approved":
            approval_summary = summary.get("approval_summary")
            if isinstance(approval_summary, dict):
                return approval_summary
        payloads = self.repository.list_payloads(execution.execution_uuid)
        for payload in payloads:
            if payload.payload_type != "approval_decision" or not isinstance(payload.content_json, dict):
                continue
            if payload.content_json.get("decision") == "approved":
                approval_summary = payload.content_json.get("approval_summary")
                if isinstance(approval_summary, dict):
                    return approval_summary
        return None

    def _linked_execution(self, execution_uuid: str) -> AIExecutionRecord | None:
        for execution in self.repository.list_executions(limit=200):
            summary = execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}
            if summary.get("approval_source_execution_id") == execution_uuid:
                return execution
        return None

    def _approval_is_still_valid(self, execution: AIExecutionRecord) -> tuple[bool, str]:
        request = self._execution_to_request(execution)
        privacy = self.orchestrator.privacy_policy.evaluate(request)
        if privacy.decision == "blocked":
            return False, "La privacidad ya no permite continuar esta ejecucion."
        approval_summary = self._approval_metadata(execution)
        resolved = self.model_registry.resolve_role(
            execution.requested_model_role or "",
            creator_id=execution.creator_id,
            provider=execution.provider,
        )
        if resolved is None:
            return False, "El modelo aprobado ya no esta disponible."
        assignment, model = resolved
        if assignment.provider != execution.provider:
            return False, "El proveedor cambio desde la aprobacion."
        if execution.model_catalog_id is not None and model.id != execution.model_catalog_id:
            return False, "El modelo cambio desde la aprobacion."
        if isinstance(approval_summary, dict):
            approved_provider = approval_summary.get("provider")
            approved_model_id = approval_summary.get("model_id")
            approved_model_catalog_id = approval_summary.get("model_catalog_id")
            if approved_provider is not None and approved_provider != execution.provider:
                return False, "El proveedor cambio desde la aprobacion."
            if approved_model_id is not None and approved_model_id != model.model_id:
                return False, "El modelo cambio desde la aprobacion."
            if approved_model_catalog_id is not None and approved_model_catalog_id != model.id:
                return False, "El modelo cambio desde la aprobacion."
        current_estimate = self.orchestrator.cost_estimator.estimate(model, input_tokens=8, output_tokens=32)
        current_cost = {
            "minimum_cost": current_estimate.minimum_cost,
            "maximum_cost": current_estimate.maximum_cost,
            "currency": current_estimate.currency,
            "pricing_version": current_estimate.pricing_version,
        }
        if approval_summary is not None:
            approved_cost = approval_summary.get("estimated_cost_at_approval")
            if not isinstance(approved_cost, dict):
                return False, "No se puede verificar el costo aprobado."
            if approved_cost.get("minimum_cost") != current_cost["minimum_cost"] or approved_cost.get("maximum_cost") != current_cost["maximum_cost"]:
                return False, "El costo estimado cambio desde la aprobacion."
            if approved_cost.get("currency") != current_cost["currency"]:
                return False, "La moneda del costo estimado cambio desde la aprobacion."
        return True, ""

    def _result_from_execution(self, execution: AIExecutionRecord) -> AIExecutionResult:
        payloads = self.repository.list_payloads(execution.execution_uuid)
        usage_records = self.repository.list_usage_records(execution.execution_uuid)
        validated_payload = next((payload for payload in payloads if payload.payload_type == "validated_result"), None)
        validation_report = next((payload for payload in payloads if payload.payload_type == "validation_report"), None)
        approval_payload = next((payload for payload in payloads if payload.payload_type == "approval_decision"), None)
        result_text = validated_payload.content_text if validated_payload else None
        structured_output = validated_payload.content_json if validated_payload else None
        validation = AIExecutionValidation(
            status=execution.validation_status or "rejected",
            schema_name=execution.task_type,
            issues=(),
            warnings=(),
        )
        if validation_report and isinstance(validation_report.content_json, dict):
            validation = AIExecutionValidation(
                status=str(validation_report.content_json.get("status") or validation.status),
                schema_name=str(validation_report.content_json.get("schema_name") or execution.task_type),
                issues=tuple(validation_report.content_json.get("issues") or ()),
                warnings=tuple(validation_report.content_json.get("warnings") or ()),
            )
        usage = AIExecutionUsage()
        if usage_records:
            record = usage_records[0]
            usage = AIExecutionUsage(
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                cached_input_tokens=record.cached_input_tokens,
                reasoning_tokens=record.reasoning_tokens,
                provider_reported_cost=record.provider_reported_cost,
                calculated_cost=record.calculated_cost,
                currency=record.currency,
                pricing_version=record.pricing_version,
                calculation_notes=record.calculation_notes,
            )
        cost = AICostSummary(
            estimated_min_cost=None,
            estimated_max_cost=None,
            calculated_cost=usage.calculated_cost if usage_records else None,
            provider_reported_cost=usage.provider_reported_cost,
            currency=usage.currency,
            pricing_version=usage.pricing_version,
            notes="Reconstructed from persisted execution.",
        )
        if isinstance(execution.input_summary_json, dict) and isinstance(execution.input_summary_json.get("approval_summary"), dict):
            approval_summary = execution.input_summary_json["approval_summary"]
        elif approval_payload and isinstance(approval_payload.content_json, dict):
            approval_summary = approval_payload.content_json.get("approval_summary")
        else:
            approval_summary = None
        provenance = {"approval": approval_summary} if isinstance(approval_summary, dict) else {}
        return AIExecutionResult(
            execution_id=execution.execution_uuid,
            request_id=str((execution.input_summary_json or {}).get("request_id") or execution.execution_uuid),
            status=execution.status,
            provider=execution.provider,
            model_id=str((execution.input_summary_json or {}).get("model_id") or execution.model_catalog_id or ""),
            model_version=str((execution.input_summary_json or {}).get("model_version") or ""),
            model_role=execution.requested_model_role,
            result=result_text,
            structured_output=structured_output if isinstance(structured_output, dict) else None,
            validation=validation,
            usage=usage,
            cost=cost,
            latency=AIExecutionLatency(
                latency_ms=execution.latency_ms,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                attempts=1,
            ),
            cache=AIExecutionCacheInfo(
                cache_status=execution.cache_status,
                cache_key=None,
                hit_count=0,
                refresh_requested=False,
            ),
            fallback={"used": False, "policy": execution.fallback_policy},
            warnings=(),
            error=None,
            provenance=provenance,
            timestamps={
                "created_at": execution.created_at,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
            },
        )

    def status(self) -> AIRuntimeStatus:
        return AIRuntimeStatus(
            ai_runtime_available=True,
            openai_configured=bool(self.credential_store.load(CredentialStore.reference_for_provider("openai"))),
            anthropic_configured=bool(self.credential_store.load(CredentialStore.reference_for_provider("anthropic"))),
            model_roles_configured=bool(self.model_registry.list_roles()),
            budget_policy_configured=self.repository.get_budget_policy(None, None) is not None,
            credential_store_available=self.credential_store.is_available(),
        )

    def list_providers(self) -> list[str]:
        return ["openai", "anthropic"]

    def provider_status(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        provider_enabled = self._runtime_setting_value("provider_enabled") or {}
        for provider in self.list_providers():
            credential = self.credential_store.load(CredentialStore.reference_for_provider(provider))
            last_check = self._runtime_setting_value("last_check", provider) or {}
            last_sync = self._runtime_setting_value("last_model_sync", provider) or {}
            result[provider] = {
                "configured": bool(credential),
                "masked_key": self.credential_store.mask(credential),
                "enabled": bool(provider_enabled.get(provider, True)) if isinstance(provider_enabled, dict) else True,
                "last_check": last_check,
                "last_model_sync": last_sync,
                "models": [entry.to_dict() for entry in self.model_registry.list_models(provider)],
                "roles": [assignment.to_dict() for assignment in self.model_registry.list_roles(provider=provider)],
            }
        return result

    def store_provider_credential(self, provider: str, api_key: str) -> None:
        self.credential_store.save(CredentialStore.reference_for_provider(provider), api_key)

    def delete_provider_credential(self, provider: str) -> None:
        self.credential_store.delete(CredentialStore.reference_for_provider(provider))

    def test_provider(self, provider: str) -> AIProviderDiagnostic:
        key = self.credential_store.load(CredentialStore.reference_for_provider(provider))
        if not key:
            diagnostic = AIProviderDiagnostic(
                provider=provider,
                configured=False,
                model_id=None,
                status="blocked",
                message="Provider credential is missing.",
            )
            self._record_provider_check(provider, diagnostic)
            return diagnostic
        client = self.providers.get(provider)
        if client is None:
            diagnostic = AIProviderDiagnostic(
                provider=provider,
                configured=True,
                model_id=None,
                status="blocked",
                message="Provider adapter is unavailable.",
            )
            self._record_provider_check(provider, diagnostic)
            return diagnostic
        diagnostic = client.test_credentials(key)
        self._record_provider_check(provider, diagnostic)
        return diagnostic

    def _record_model_sync(self, provider: str, report: AIProviderModelSyncReport) -> None:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="provider",
                scope_id=provider,
                setting_key="last_model_sync",
                setting_value_json=report.to_dict(),
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def _model_meets_role_requirements(self, role: str, model: AIModelCatalogEntry) -> tuple[bool, tuple[str, ...]]:
        requirements = self.ROLE_REQUIREMENTS.get(role, {})
        notes: list[str] = []
        capabilities = model.capabilities_json if isinstance(model.capabilities_json, dict) else {}
        for capability, required in requirements.items():
            if not required:
                continue
            value = capabilities.get(capability)
            if value is None:
                value = getattr(model, f"supports_{capability}", False)
            if value is False:
                notes.append(f"Missing capability: {capability}")
        return not notes, tuple(notes)

    def _model_text_haystack(self, model: AIModelCatalogEntry) -> str:
        return " ".join(
            part
            for part in (
                model.provider,
                model.model_id,
                model.display_name,
                model.snapshot_or_version or "",
                model.replacement_model_id or "",
                " ".join(str(key) for key in (model.capabilities_json or {}).keys()) if isinstance(model.capabilities_json, dict) else "",
            )
        ).lower()

    def _model_tokens(self, model: AIModelCatalogEntry) -> set[str]:
        return {token for token in re.split(r"[^a-z0-9]+", self._model_text_haystack(model)) if token}

    def _model_is_preview_like(self, model: AIModelCatalogEntry, tokens: set[str]) -> bool:
        return "preview" in tokens

    def _model_is_snapshot_like(self, model: AIModelCatalogEntry, tokens: set[str]) -> bool:
        if model.snapshot_or_version is not None:
            return True
        return any(token.isdigit() and len(token) >= 4 for token in tokens)

    def _model_has_known_specialization(self, model: AIModelCatalogEntry, tokens: set[str], role: str) -> tuple[bool, str | None]:
        blocked = self.ROLE_BLOCKED_KEYWORDS.get(role, ())
        if any(any(token.startswith(prefix) for token in tokens) for prefix in blocked):
            return True, "Modelo especializado incompatible con este rol."
        if role == "multimodal_model":
            if not (model.supports_image_input or any(token in tokens for token in ("image", "vision", "multimodal"))):
                return True, "Falta confirmacion de entrada de imagen."
            return False, None
        if role == "transcription_fallback_model":
            if not (model.supports_audio_input or any(token in tokens for token in ("transcription", "whisper", "speech", "audio"))):
                return True, "Falta confirmacion de transcripcion o audio."
            return False, None
        return False, None

    def _model_selection_category(self, role: str, model: AIModelCatalogEntry) -> tuple[str, str, str | None]:
        classification = classify_model_for_role(model, role)
        compatibility_state = str(classification.get("compatibility_state") or "compatibility_unknown")
        reason = classification.get("reason")
        if compatibility_state == "incompatible_confirmed":
            return "incompatible", "Incompatible", str(reason or "El modelo no es compatible.")
        if compatibility_state == "compatible_verified_catalog":
            return "recommended", "Recomendado", str(reason or None)
        if compatibility_state == "compatible_by_verified_catalog":
            return "compatible", "Compatible", str(reason or None)
        if compatibility_state == "compatibility_unknown":
            tokens = self._model_tokens(model)
            if self._model_is_preview_like(model, tokens):
                return "preview", "Preview", str(reason or "Vista previa o variante experimental.")
            if self._model_is_snapshot_like(model, tokens):
                return "advanced", "Avanzado", str(reason or "Variante snapshot o tecnica.")
            return "compatible", "Compatible", str(reason or "Modelo disponible en la cuenta, pero todavia no evaluado por Creator Intelligence Studio.")
        if model.status == "testing":
            return "compatible", "Compatible", "Compatible, pendiente de evaluacion."
        return "recommended", "Recomendado", None

    def _model_selection_score(self, model: AIModelCatalogEntry, category: str) -> tuple[int, int, int, str, str]:
        tokens = self._model_tokens(model)
        stable_bonus = 1 if model.status == "approved" else 0
        price_known = 1 if model.input_price_per_million is not None or model.output_price_per_million is not None else 0
        snapshot_penalty = 1 if model.snapshot_or_version else 0
        preview_penalty = 1 if "preview" in tokens else 0
        size_bonus = 0
        for token in tokens:
            if token in {"mini", "small", "nano"}:
                size_bonus += 2
            elif token in {"fast", "light", "lite"}:
                size_bonus += 1
        category_rank = {
            "recommended": 0,
            "compatible": 1,
            "advanced": 2,
            "preview": 3,
            "deprecated": 4,
            "incompatible": 5,
            "unavailable": 6,
            "blocked": 7,
        }.get(category, 8)
        return (-category_rank, stable_bonus + price_known + size_bonus, -snapshot_penalty - preview_penalty, model.display_name.lower(), model.model_id.lower())

    def _build_selection_row(self, role: str, model: AIModelCatalogEntry, *, force_visible: bool = False) -> dict[str, object]:
        category, category_label, reason = self._model_selection_category(role, model)
        tokens = self._model_tokens(model)
        price_text = "Precio pendiente de verificar"
        if model.input_price_per_million is not None or model.output_price_per_million is not None:
            price_text = f"{model.input_price_per_million or '-'} / {model.output_price_per_million or '-'} {model.pricing_currency or 'USD'}"
        capability_bits: list[str] = []
        capabilities = model.capabilities_json if isinstance(model.capabilities_json, dict) else {}
        for key, value in sorted(capabilities.items()):
            if isinstance(value, bool):
                if value:
                    capability_bits.append(str(key))
            elif value is not None:
                capability_bits.append(f"{key}={value}")
        if not capability_bits:
            if model.supports_structured_output:
                capability_bits.append("structured_output")
            if model.supports_image_input:
                capability_bits.append("image_input")
            if model.supports_audio_input:
                capability_bits.append("audio_input")
        classification = classify_model_for_role(model, role)
        compatibility_state = str(classification.get("compatibility_state") or "compatibility_unknown")
        recommendation_label = str(classification.get("recommendation_tag") or category_label)
        if category in {"compatible", "recommended"} and price_text == "Precio pendiente de verificar":
            recommendation_label = "Compatible, pendiente de evaluacion"
        if category == "advanced" and model.snapshot_or_version:
            recommendation_label = "Avanzado"
        detail_lines = [
            f"Proveedor: {model.provider}",
            f"Modelo: {model.model_id}",
            f"Estado: {model.status}",
            f"Version: {model.snapshot_or_version or 'sin snapshot'}",
            f"Capacidades: {', '.join(capability_bits) if capability_bits else '-'}",
            f"Precio: {price_text}",
            f"Ultima verificacion: {model.last_verified_at or 'sin verificacion'}",
        ]
        if reason:
            detail_lines.append(f"Nota: {reason}")
        visible = force_visible or bool(classification.get("is_visible_by_default")) or category in {"recommended", "compatible", "advanced"}
        if category in {"preview", "deprecated", "incompatible", "unavailable", "blocked"}:
            visible = force_visible
        return {
            "provider": model.provider,
            "model_id": model.model_id,
            "display_name": model.display_name,
            "snapshot_or_version": model.snapshot_or_version,
            "status": model.status,
            "capabilities_json": model.capabilities_json,
            "category": category,
            "category_label": category_label,
            "compatibility_state": compatibility_state,
            "recommendation_label": recommendation_label,
            "display_label": f"{category_label} · {model.display_name} ({model.model_id})",
            "detail_text": "\n".join(detail_lines),
            "warning": reason,
            "price_text": price_text,
            "capabilities_text": ", ".join(capability_bits) if capability_bits else "-",
            "is_recommended": category == "recommended",
            "is_compatible": category in {"recommended", "compatible"},
            "is_advanced": category == "advanced",
            "is_preview": category == "preview",
            "is_deprecated": category == "deprecated",
            "is_incompatible": category == "incompatible",
            "is_hidden_by_default": category in {"preview", "deprecated", "incompatible", "unavailable", "blocked"},
            "is_visible": visible,
            "sort_key": self._model_selection_score(model, category),
            "search_text": " ".join(
                part for part in (model.display_name, model.model_id, model.snapshot_or_version or "", category_label, recommendation_label, price_text, " ".join(capability_bits)) if part
            ).lower(),
        }

    def guided_configuration_summary(self, provider: str, *, profile_key: str = "equilibrado", creator_id: str | None = None) -> dict[str, object]:
        catalog = self.model_registry.list_models(provider)
        assignments = self.model_registry.list_roles(creator_id=creator_id, provider=provider)
        sync_setting = self._runtime_setting_value("last_model_sync", provider)
        synchronized_at = None
        if isinstance(sync_setting, dict):
            synchronized_at = str(sync_setting.get("checked_at") or sync_setting.get("updated_at") or sync_setting.get("created_at") or "") or None
        summary = self.recommended_model_resolver.summarize_provider(
            provider=provider,
            catalog=catalog,
            assignments=assignments,
            profile_key=profile_key,
            synchronized_at=synchronized_at,
        )
        return summary.to_dict()

    def apply_recommended_configuration(
        self,
        provider: str,
        *,
        profile_key: str = "equilibrado",
        creator_id: str | None = None,
        replace_existing: bool = True,
    ) -> dict[str, object]:
        summary = self.guided_configuration_summary(provider, profile_key=profile_key, creator_id=creator_id)
        applied: list[dict[str, object]] = []
        skipped: list[dict[str, object]] = []
        for role in summary.get("roles", []):
            if not isinstance(role, dict):
                continue
            if not role.get("required_now"):
                continue
            proposed = role.get("proposed_model")
            if not isinstance(proposed, dict) or not proposed:
                skipped.append({"role": role.get("role"), "reason": "No recommended model available."})
                continue
            current = role.get("current_assignment")
            if isinstance(current, dict) and current.get("model_catalog_id") and current.get("model_catalog_id") != proposed.get("id") and not replace_existing:
                skipped.append({"role": role.get("role"), "reason": "Existing assignment kept by user choice."})
                continue
            assignment = self.assign_role(
                role=str(role.get("role") or ""),
                provider=provider,
                model_id=str(proposed.get("model_id") or ""),
                creator_id=creator_id,
                display_name=str(proposed.get("display_name") or proposed.get("model_id") or ""),
                is_default=True,
                is_enabled=True,
                fallback_policy="none",
                quality_level="standard",
                status=str(proposed.get("status") or "testing"),
                capabilities_json=dict(proposed.get("capabilities_json") or {}),
                snapshot_or_version=proposed.get("snapshot_or_version"),
            )
            applied.append(assignment)
        refreshed = self.guided_configuration_summary(provider, profile_key=profile_key, creator_id=creator_id)
        return {
            "provider": provider,
            "profile_key": profile_key,
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "applied": applied,
            "skipped": skipped,
            "summary": refreshed,
        }

    def list_assignable_models(self, provider: str, role: str) -> list[dict[str, object]]:
        selection = self.list_model_selection(provider, role)
        models = []
        for item in selection["items"]:
            if item.get("is_visible") and item.get("category") in {"recommended", "compatible", "advanced"}:
                models.append(item)
        return models

    def list_model_selection(
        self,
        provider: str,
        role: str,
        *,
        query: str | None = None,
        mode: str = "compatible",
        show_non_recommended: bool = False,
        show_all_models: bool = False,
        show_snapshots_and_previews: bool = False,
        selected_model_id: str | None = None,
    ) -> dict[str, object]:
        raw_models = list(self.model_registry.list_models(provider))
        selected_model = None
        if selected_model_id:
            selected_model = next((model for model in raw_models if model.model_id == selected_model_id), None)
        rows: list[dict[str, object]] = []
        counts = {"recommended": 0, "compatible": 0, "compatibility_unknown": 0, "advanced": 0, "preview": 0, "deprecated": 0, "incompatible": 0, "unavailable": 0, "blocked": 0}
        for model in raw_models:
            row = self._build_selection_row(role, model, force_visible=bool(selected_model and model.model_id == selected_model.model_id))
            category_key = str(row["category"])
            counts[category_key] = counts.get(category_key, 0) + 1
            if str(row.get("compatibility_state") or "") == "compatibility_unknown":
                counts["compatibility_unknown"] = counts.get("compatibility_unknown", 0) + 1
            if query:
                needle = query.strip().lower()
                if needle and needle not in row["search_text"]:
                    if not (selected_model and model.model_id == selected_model.model_id):
                        continue
            if show_all_models:
                row["is_visible"] = True
            if not show_all_models:
                if not show_snapshots_and_previews and row["category"] == "preview":
                    if not (selected_model and model.model_id == selected_model.model_id):
                        continue
                if mode == "recommended" and row["category"] != "recommended":
                    if not (selected_model and model.model_id == selected_model.model_id):
                        continue
                if mode == "compatible" and row["category"] not in {"recommended", "compatible"}:
                    if not show_non_recommended or row["category"] != "advanced":
                        if not (selected_model and model.model_id == selected_model.model_id):
                            continue
                if mode == "all" and row["category"] == "preview" and not show_snapshots_and_previews:
                    if not (selected_model and model.model_id == selected_model.model_id):
                        continue
                if not show_non_recommended and row["category"] == "advanced" and mode != "all":
                    if not (selected_model and model.model_id == selected_model.model_id):
                        continue
            rows.append(row)
        rows.sort(key=lambda item: item["sort_key"])
        if selected_model and selected_model.model_id not in {row["model_id"] for row in rows}:
            row = self._build_selection_row(role, selected_model, force_visible=True)
            row["warning"] = row["warning"] or "Asignacion existente conservada."
            row["is_visible"] = True
            rows.insert(0, row)
        visible_rows = [row for row in rows if row.get("is_visible")]
        return {
            "provider": provider,
            "role": role,
            "catalog_count": len(raw_models),
            "recommended_count": counts["recommended"],
            "compatible_count": counts["recommended"] + counts["compatible"],
            "unknown_count": counts["compatibility_unknown"],
            "advanced_count": counts["advanced"],
            "preview_count": counts["preview"],
            "deprecated_count": counts["deprecated"],
            "incompatible_count": counts["incompatible"],
            "unavailable_count": counts["unavailable"],
            "blocked_count": counts["blocked"],
            "visible_count": len(visible_rows),
            "selected_model_id": selected_model_id,
            "items": rows,
        }

    def refresh_provider_models(self, provider: str) -> dict[str, object]:
        credential = self.credential_store.load(CredentialStore.reference_for_provider(provider))
        if not credential:
            error = AIExecutionError(
                category="authentication_error",
                safe_message=f"No hay una credencial configurada para {provider}.",
                retryable=False,
                suggested_action="Store the provider API key.",
                technical_reference=CredentialStore.reference_for_provider(provider),
            )
            report = AIProviderModelSyncReport(
                provider=provider,
                status="blocked",
                message=error.safe_message,
                error=error,
            )
            self._record_model_sync(provider, report)
            return report.to_dict()
        client = self.providers.get(provider)
        if client is None:
            error = AIExecutionError(
                category="provider_error",
                safe_message="Provider adapter is unavailable.",
                retryable=False,
                suggested_action="Register the provider adapter.",
                technical_reference="adapter",
            )
            report = AIProviderModelSyncReport(
                provider=provider,
                status="blocked",
                message=error.safe_message,
                error=error,
            )
            self._record_model_sync(provider, report)
            return report.to_dict()

        report = client.discover_models(credential)
        if report.status != "ok":
            self._record_model_sync(provider, report)
            return report.to_dict()
        existing_models = self.repository.list_model_catalog_entries(provider)
        now = self._now()
        new_count = 0
        updated_count = 0
        unavailable_count = 0
        discovered_keys = {(model.model_id, model.snapshot_or_version) for model in report.models}
        for discovered in report.models:
            current = next(
                (
                    entry
                    for entry in existing_models
                    if entry.model_id == discovered.model_id and entry.snapshot_or_version == discovered.snapshot_or_version
                ),
                None,
            )
            entry = AIModelCatalogEntry(
                id=current.id if current else None,
                provider=discovered.provider,
                model_id=discovered.model_id,
                display_name=discovered.display_name,
                snapshot_or_version=discovered.snapshot_or_version,
                status=discovered.status,
                capabilities_json=discovered.capabilities_json,
                context_limit=discovered.context_limit,
                supports_structured_output=discovered.supports_structured_output,
                supports_image_input=discovered.supports_image_input,
                supports_audio_input=discovered.supports_audio_input,
                input_price_per_million=discovered.input_price_per_million,
                output_price_per_million=discovered.output_price_per_million,
                cached_input_price_per_million=discovered.cached_input_price_per_million,
                pricing_currency=discovered.pricing_currency,
                pricing_effective_at=discovered.pricing_effective_at,
                last_verified_at=now,
                replacement_model_id=discovered.replacement_model_id,
                created_at=current.created_at if current else now,
                updated_at=now,
            )
            self.repository.upsert_model_catalog_entry(entry)
            if current is None:
                new_count += 1
            else:
                updated_count += 1
        for entry in existing_models:
            if (entry.model_id, entry.snapshot_or_version) in discovered_keys:
                continue
            if entry.status in {"deprecated", "unavailable", "blocked"}:
                continue
            self.repository.upsert_model_catalog_entry(
                AIModelCatalogEntry(
                    id=entry.id,
                    provider=entry.provider,
                    model_id=entry.model_id,
                    display_name=entry.display_name,
                    snapshot_or_version=entry.snapshot_or_version,
                    status="unavailable",
                    capabilities_json=entry.capabilities_json,
                    context_limit=entry.context_limit,
                    supports_structured_output=entry.supports_structured_output,
                    supports_image_input=entry.supports_image_input,
                    supports_audio_input=entry.supports_audio_input,
                    input_price_per_million=entry.input_price_per_million,
                    output_price_per_million=entry.output_price_per_million,
                    cached_input_price_per_million=entry.cached_input_price_per_million,
                    pricing_currency=entry.pricing_currency,
                    pricing_effective_at=entry.pricing_effective_at,
                    last_verified_at=now,
                    replacement_model_id=entry.replacement_model_id,
                    created_at=entry.created_at,
                    updated_at=now,
                )
            )
            unavailable_count += 1
        final = replace(
            report,
            status="ok",
            message="Provider model catalog synchronized.",
            found_count=len(report.models),
            compatible_count=sum(1 for model in report.models if model.status in {"approved", "testing"}),
            new_count=new_count,
            updated_count=updated_count,
            unavailable_count=unavailable_count,
            checked_at=now,
        )
        self._record_model_sync(provider, final)
        return final.to_dict()

    def list_models(self, provider: str | None = None) -> list[dict[str, object]]:
        return [entry.to_dict() for entry in self.model_registry.list_models(provider)]

    def verify_models(self, provider: str) -> dict[str, object]:
        return self.refresh_provider_models(provider)

    def list_roles(self, creator_id: str | None = None) -> list[dict[str, object]]:
        return [assignment.to_dict() for assignment in self.model_registry.list_roles(creator_id=creator_id)]

    def assign_role(
        self,
        *,
        role: str,
        provider: str,
        model_id: str,
        creator_id: str | None = None,
        display_name: str | None = None,
        is_default: bool = False,
        is_enabled: bool = True,
        fallback_policy: str = "none",
        quality_level: str = "standard",
        status: str = "testing",
        capabilities_json: dict[str, object] | None = None,
        snapshot_or_version: str | None = None,
    ) -> dict[str, object]:
        candidates = [
            entry
            for entry in self.model_registry.list_models(provider)
            if entry.model_id == model_id and (snapshot_or_version is None or entry.snapshot_or_version == snapshot_or_version)
        ]
        if not candidates:
            raise ValueError("No synchronized model is available for the requested provider and model id.")
        model = candidates[0]
        if model.status not in {"approved", "testing"}:
            raise ValueError("The selected model is not currently usable.")
        allowed, notes = self._model_meets_role_requirements(role, model)
        if not allowed:
            raise ValueError("; ".join(notes) or "The selected model does not satisfy the role requirements.")
        assignment = self.model_registry.assign_role(
            role=role,
            provider=provider,
            model_id=model_id,
            creator_id=creator_id,
            display_name=display_name,
            is_default=is_default,
            is_enabled=is_enabled,
            fallback_policy=fallback_policy,
            quality_level=quality_level,
            status=status,
            capabilities_json=capabilities_json if capabilities_json is not None else model.capabilities_json,
            snapshot_or_version=snapshot_or_version,
        )
        return assignment.to_dict()

    def get_budget_policy(self, creator_id: str | None = None, provider: str | None = None) -> dict[str, object] | None:
        policy = self.repository.get_budget_policy(creator_id, provider)
        return policy.to_dict() if policy else None

    def set_monthly_budget(self, amount: float, currency: str, creator_id: str | None = None, provider: str | None = None) -> dict[str, object]:
        current = self.repository.get_budget_policy(creator_id, provider) or AIBudgetPolicy(creator_id=creator_id, provider=provider, created_at=self._now(), updated_at=self._now())
        updated = self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                id=current.id,
                creator_id=creator_id,
                provider=provider,
                daily_limit=current.daily_limit,
                monthly_limit=amount,
                per_task_limit=current.per_task_limit,
                warning_threshold_50=current.warning_threshold_50,
                warning_threshold_75=current.warning_threshold_75,
                warning_threshold_90=current.warning_threshold_90,
                hard_block_enabled=current.hard_block_enabled,
                currency=currency,
                effective_from=current.effective_from or self._now(),
                effective_until=current.effective_until,
                created_at=current.created_at or self._now(),
                updated_at=self._now(),
            )
        )
        return updated.to_dict()

    def set_per_task_budget(self, amount: float, currency: str, creator_id: str | None = None, provider: str | None = None) -> dict[str, object]:
        current = self.repository.get_budget_policy(creator_id, provider) or AIBudgetPolicy(creator_id=creator_id, provider=provider, created_at=self._now(), updated_at=self._now())
        updated = self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                id=current.id,
                creator_id=creator_id,
                provider=provider,
                daily_limit=current.daily_limit,
                monthly_limit=current.monthly_limit,
                per_task_limit=amount,
                warning_threshold_50=current.warning_threshold_50,
                warning_threshold_75=current.warning_threshold_75,
                warning_threshold_90=current.warning_threshold_90,
                hard_block_enabled=current.hard_block_enabled,
                currency=currency,
                effective_from=current.effective_from or self._now(),
                effective_until=current.effective_until,
                created_at=current.created_at or self._now(),
                updated_at=self._now(),
            )
        )
        return updated.to_dict()

    def update_budget_policy(
        self,
        *,
        creator_id: str | None = None,
        provider: str | None = None,
        monthly_limit: float | None = None,
        per_task_limit: float | None = None,
        hard_block_enabled: bool = True,
        currency: str = "USD",
        approval_threshold: float | None = None,
    ) -> dict[str, object]:
        current = self.repository.get_budget_policy(creator_id, provider) or AIBudgetPolicy(creator_id=creator_id, provider=provider, created_at=self._now(), updated_at=self._now())
        updated = self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                id=current.id,
                creator_id=creator_id,
                provider=provider,
                daily_limit=current.daily_limit,
                monthly_limit=monthly_limit,
                per_task_limit=per_task_limit,
                warning_threshold_50=current.warning_threshold_50,
                warning_threshold_75=current.warning_threshold_75,
                warning_threshold_90=approval_threshold if approval_threshold is not None else current.warning_threshold_90,
                hard_block_enabled=hard_block_enabled,
                currency=currency,
                effective_from=current.effective_from or self._now(),
                effective_until=current.effective_until,
                created_at=current.created_at or self._now(),
                updated_at=self._now(),
            )
        )
        return updated.to_dict()

    def budget_snapshot(self, creator_id: str | None = None, provider: str | None = None) -> dict[str, object]:
        policy = self.get_budget_policy(creator_id, provider)
        provider_enabled = self._runtime_setting_value("provider_enabled") or {}
        cross_provider = self._runtime_setting_value("cross_provider_fallback_enabled") or {}
        approval_threshold = self._runtime_setting_value("cost_approval_threshold") or {}
        executions = self.repository.list_executions(creator_id=creator_id, provider=provider, limit=1000)
        usage_records = self.repository.list_usage_records()
        monthly_cost = 0.0
        provider_costs: dict[str, float] = {}
        calls = 0
        billing_errors = 0
        warnings: list[str] = []
        for execution in executions:
            calls += 1
            if execution.error_category == "billing_error":
                billing_errors += 1
            try:
                created_at = execution.created_at
                if created_at is None:
                    continue
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created.year == now.year and created.month == now.month:
                    for record in usage_records:
                        if record.execution_id == execution.execution_uuid:
                            monthly_cost += record.calculated_cost
                            provider_costs[record.provider] = provider_costs.get(record.provider, 0.0) + record.calculated_cost
            except Exception:
                continue
        if policy is not None and policy.get("monthly_limit") is not None and monthly_cost > float(policy["monthly_limit"]):
            warnings.append("Monthly consumption exceeds the configured limit.")
        if any(entry.get("input_price_per_million") is None or entry.get("output_price_per_million") is None for entry in self.list_models()):
            warnings.append("Precio pendiente de verificar para uno o mas modelos.")
        return {
            "policy": policy,
            "monthly_cost": round(monthly_cost, 8),
            "provider_costs": {provider_name: round(value, 8) for provider_name, value in provider_costs.items()},
            "calls": calls,
            "billing_errors": billing_errors,
            "provider_enabled": provider_enabled,
            "cross_provider_fallback_enabled": bool(cross_provider.get("enabled", True)) if isinstance(cross_provider, dict) else True,
            "approval_threshold": float(approval_threshold.get("value")) if isinstance(approval_threshold, dict) and approval_threshold.get("value") is not None else (policy.get("warning_threshold_90") if policy else None),
            "warnings": tuple(warnings),
            "usage_records": [record.to_dict() for record in usage_records],
        }

    def diagnostic_run(
        self,
        *,
        provider: str | None = None,
        role: str | None = None,
        cache_policy: str = "use",
    ) -> AIExecutionResult:
        return self.orchestrator.run_diagnostic(provider=provider, role=role, cache_policy=cache_policy)

    def approve_and_run_diagnostic(
        self,
        execution_uuid: str,
        *,
        approved_by: str | None = None,
        approval_reason: str | None = None,
    ) -> AIExecutionResult:
        execution = self.repository.get_execution_by_uuid(execution_uuid)
        if execution is None:
            raise ValueError("Execution not found.")
        if execution.status == "cancelled":
            raise ValueError("Execution was cancelled and cannot be approved.")

        linked = self._linked_execution(execution_uuid)
        if linked is not None:
            return self._result_from_execution(linked)

        if execution.status != "awaiting_approval":
            raise ValueError("Execution is not waiting for approval.")

        request = self._execution_to_request(execution)
        valid, invalid_reason = self._approval_is_still_valid(execution)
        if not valid:
            now = self._now()
            payload = self._approval_payload(execution=execution, approved=False, actor=approved_by, reason=invalid_reason, now=now)
            payload["decision"] = "invalidated"
            self.repository.store_payload(
                AIExecutionPayload(
                    execution_id=execution.execution_uuid,
                    payload_type="approval_decision",
                    content_json=payload,
                    content_text="invalidated",
                    content_hash=execution.request_fingerprint,
                    is_redacted=False,
                    retention_class="diagnostic",
                    created_at=now,
                )
            )
            updated = self.repository.store_execution(
                replace(
                    execution,
                    status="cancelled",
                    validation_status="requires_human_review",
                    completed_at=now,
                    latency_ms=0,
                    error_category="budget_block",
                    error_code=None,
                    error_message_safe=invalid_reason,
                    approved_at=execution.approved_at or now,
                    updated_at=now,
                    input_summary_json={
                        **(execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}),
                        "approval_state": "invalidated",
                        "approval_invalidated_reason": invalid_reason,
                        "approval_invalidated_at": now,
                    },
                )
            )
            return AIExecutionResult(
                execution_id=updated.execution_uuid,
                request_id=request.request_id,
                status="failed",
                provider=updated.provider,
                model_id=str((updated.input_summary_json or {}).get("model_id") or updated.model_catalog_id or ""),
                model_version=str((updated.input_summary_json or {}).get("model_version") or ""),
                model_role=updated.requested_model_role,
                result=None,
                structured_output=None,
                validation=AIExecutionValidation(status="requires_human_review", schema_name=updated.task_type, issues=(invalid_reason,), warnings=()),
                usage=AIExecutionUsage(),
                cost=AICostSummary(None, None, calculated_cost=None, provider_reported_cost=None, currency="USD", notes=invalid_reason),
                latency=AIExecutionLatency(latency_ms=0, started_at=updated.started_at or now, completed_at=now, attempts=1),
                cache=AIExecutionCacheInfo(cache_status="invalidated"),
                fallback={"used": False, "policy": updated.fallback_policy},
                warnings=(),
                error=AIExecutionError(category="budget_block", safe_message=invalid_reason, suggested_action="Revisar la aprobacion o volver a ejecutar con un modelo compatible."),
                provenance={"approval": self._approval_metadata(updated), "approval_state": "invalidated"},
                timestamps={"created_at": updated.created_at, "started_at": updated.started_at, "completed_at": now},
            )

        now = self._now()
        approval_summary = self._approval_metadata(execution)
        payload = self._approval_payload(execution=execution, approved=True, actor=approved_by, reason=approval_reason, now=now)
        payload["approval_summary"] = approval_summary or payload["approval_summary"]
        self.repository.store_payload(
            AIExecutionPayload(
                execution_id=execution.execution_uuid,
                payload_type="approval_decision",
                content_json=payload,
                content_text="approved",
                content_hash=execution.request_fingerprint,
                is_redacted=False,
                retention_class="diagnostic",
                created_at=now,
            )
        )
        self.repository.store_execution(
            replace(
                execution,
                approved_at=now,
                input_summary_json={
                    **(execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}),
                    "approval_state": "approved",
                    "approved_by": approved_by,
                    "approved_at": now,
                    "approval_reason": approval_reason,
                },
                updated_at=now,
            )
        )

        approval_source_metadata = {
            "approval_source_execution_id": execution.execution_uuid,
            "approval_state": "approved",
            "approved_by": approved_by,
            "approved_at": now,
            "approval_reason": approval_reason,
            "approval_scope": "single_execution",
            "provider_at_approval": execution.provider,
            "model_at_approval": execution.model_catalog_id,
        }
        request = replace(
            request,
            request_id=f"{request.request_id}:approved:{execution.execution_uuid}",
            approval_policy="approved_single_execution",
            metadata={**request.metadata, **approval_source_metadata},
        )
        result = self.orchestrator.run(request, provider=execution.provider)
        return result

    def reject_diagnostic_execution(
        self,
        execution_uuid: str,
        *,
        rejected_by: str | None = None,
        rejection_reason: str | None = None,
    ) -> dict[str, object]:
        execution = self.repository.get_execution_by_uuid(execution_uuid)
        if execution is None:
            raise ValueError("Execution not found.")
        if execution.status == "cancelled":
            return execution.to_dict()
        now = self._now()
        payload = self._approval_payload(execution=execution, approved=False, actor=rejected_by, reason=rejection_reason, now=now)
        self.repository.store_payload(
            AIExecutionPayload(
                execution_id=execution.execution_uuid,
                payload_type="approval_decision",
                content_json=payload,
                content_text="rejected",
                content_hash=execution.request_fingerprint,
                is_redacted=False,
                retention_class="diagnostic",
                created_at=now,
            )
        )
        updated = self.repository.store_execution(
            replace(
                execution,
                status="cancelled",
                validation_status="requires_human_review",
                completed_at=now,
                latency_ms=0,
                error_category="cancelled_by_user",
                error_code=None,
                error_message_safe="La ejecucion fue cancelada y no se realizo ningun cargo.",
                approved_at=None,
                updated_at=now,
                input_summary_json={
                    **(execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}),
                    "approval_state": "rejected",
                    "rejected_by": rejected_by,
                    "rejected_at": now,
                    "rejection_reason": rejection_reason,
                },
            )
        )
        return updated.to_dict()

    def recover_orphaned_diagnostic_executions(self) -> list[dict[str, object]]:
        recovered: list[dict[str, object]] = []
        now = self._now()
        for execution in self.repository.list_executions(limit=200):
            if execution.task_type != "provider_diagnostic":
                continue
            if execution.status not in {"queued", "preparing_context", "running", "validating"}:
                continue
            updated = self.repository.store_execution(
                replace(
                    execution,
                    status="cancelled",
                    validation_status="rejected",
                    completed_at=execution.completed_at or now,
                    latency_ms=execution.latency_ms or 0,
                    error_category="interrupted",
                    error_code=None,
                    error_message_safe="La ejecucion anterior se interrumpio al cerrar la aplicacion. Puedes volver a intentarla.",
                    approved_at=execution.approved_at,
                    updated_at=now,
                    input_summary_json={
                        **(execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}),
                        "recovery_state": "interrupted",
                        "interrupted_at": now,
                        "interrupted_reason": "startup_recovery",
                        "retry_allowed": True,
                    },
                )
            )
            recovered.append(updated.to_dict())
        return recovered

    def cancel_diagnostic_execution(
        self,
        execution_uuid: str,
        *,
        cancelled_by: str | None = None,
        cancellation_reason: str | None = None,
    ) -> dict[str, object]:
        execution = self.repository.get_execution_by_uuid(execution_uuid)
        if execution is None:
            raise ValueError("Execution not found.")
        if execution.task_type != "provider_diagnostic":
            raise ValueError("Execution is not a diagnostic run.")
        if execution.status in {"completed", "completed_with_warnings", "failed", "cancelled", "blocked_by_budget", "blocked_by_privacy", "blocked_by_credentials", "blocked_by_provider", "blocked_by_model"}:
            return execution.to_dict()
        now = self._now()
        updated = self.repository.store_execution(
            replace(
                execution,
                status="cancelled",
                validation_status="rejected" if execution.status == "awaiting_approval" else execution.validation_status,
                completed_at=now,
                latency_ms=execution.latency_ms or 0,
                error_category="cancelled_by_user" if cancelled_by else "interrupted",
                error_code=None,
                error_message_safe=cancellation_reason or "La ejecucion anterior se interrumpio al cerrar la aplicacion. Puedes volver a intentarla.",
                approved_at=execution.approved_at,
                updated_at=now,
                input_summary_json={
                    **(execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}),
                    "recovery_state": "cancelled_by_user" if cancelled_by else "interrupted",
                    "cancelled_by": cancelled_by,
                    "cancelled_at": now,
                    "cancelled_reason": cancellation_reason,
                    "retry_allowed": True,
                },
            )
        )
        return updated.to_dict()

    def list_executions(self, creator_id: str | None = None, provider: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        return [execution.to_dict() for execution in self.repository.list_executions(creator_id=creator_id, provider=provider, limit=limit)]

    def get_execution(self, execution_uuid: str) -> dict[str, object] | None:
        execution = self.repository.get_execution_by_uuid(execution_uuid)
        return execution.to_dict() if execution else None

    def list_usage_records(self, execution_id: str | None = None) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.repository.list_usage_records(execution_id)]

    def list_payloads(self, execution_id: str) -> list[dict[str, object]]:
        return [payload.to_dict() for payload in self.repository.list_payloads(execution_id)]

    def diagnostics_snapshot(self) -> dict[str, object]:
        status = self.status()
        return {
            "ai_runtime_available": status.ai_runtime_available,
            "openai_configured": status.openai_configured,
            "anthropic_configured": status.anthropic_configured,
            "model_roles_configured": status.model_roles_configured,
            "budget_policy_configured": status.budget_policy_configured,
            "credential_store_available": status.credential_store_available,
        }


def build_ai_runtime_service(*, settings: AppSettings, paths: ProjectPaths, database: SQLiteDatabase, credential_store: CredentialStore | None = None) -> AIRuntimeService:
    repository = SQLiteAIRuntimeRepository(database)
    credential_store = credential_store or CredentialStore.build_default()
    return AIRuntimeService(
        settings=settings,
        paths=paths,
        database=database,
        credential_store=credential_store,
        repository=repository,
    )
