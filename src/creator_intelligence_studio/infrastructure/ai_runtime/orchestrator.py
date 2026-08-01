"""AI orchestration for controlled provider execution."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4
from typing import Any

from .cache import AICache
from .credentials import CredentialStore
from .models import (
    AICacheEntry,
    AICostSummary,
    AICacheStatus,
    AIExecutionCacheInfo,
    AIExecutionError,
    AIExecutionLatency,
    AIExecutionPayload,
    AIExecutionRecord,
    AIExecutionRequest,
    AIExecutionResult,
    AIExecutionUsage,
    AIExecutionValidation,
    AIUsageRecord,
    AIModelCatalogEntry,
    AIProviderResponse,
    AIPromptTemplate,
    AIRoleAssignment,
    build_request_fingerprint,
)
from .policies import AIResultValidator, BudgetPolicy, CostEstimator, CostTracker, PrivacyPolicyEngine
from .providers import AIProvider
from .registry import ModelRegistry, PromptRegistry
from .repository import SQLiteAIRuntimeRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_ACTIVE_EXECUTION_STATUSES = {
    "queued",
    "preparing_context",
    "awaiting_approval",
    "running",
    "validating",
}


logger = logging.getLogger(__name__)


class AIOrchestrator:
    def __init__(
        self,
        *,
        model_registry: ModelRegistry,
        prompt_registry: PromptRegistry,
        credential_store: CredentialStore,
        repository: SQLiteAIRuntimeRepository,
        providers: dict[str, AIProvider],
        privacy_policy: PrivacyPolicyEngine | None = None,
        cost_estimator: CostEstimator | None = None,
        cost_tracker: CostTracker | None = None,
        result_validator: AIResultValidator | None = None,
        cache: AICache | None = None,
        max_retries: int = 2,
    ) -> None:
        self.model_registry = model_registry
        self.prompt_registry = prompt_registry
        self.credential_store = credential_store
        self.repository = repository
        self.providers = providers
        self.privacy_policy = privacy_policy or PrivacyPolicyEngine()
        self.cost_estimator = cost_estimator or CostEstimator()
        self.cost_tracker = cost_tracker or CostTracker()
        self.result_validator = result_validator or AIResultValidator()
        self.cache = cache or AICache(repository)
        self.max_retries = max(0, min(2, max_retries))

    def _provider_enabled(self, provider_name: str) -> bool:
        setting = self.repository.get_runtime_setting("application", "provider_enabled")
        if setting is None:
            return True
        value = setting.setting_value_json
        if isinstance(value, dict):
            enabled = value.get(provider_name)
            if enabled is None:
                return True
            return bool(enabled)
        return True

    def _request_summary(
        self,
        *,
        request: AIExecutionRequest,
        privacy: Any,
        request_hash: str,
        context_fingerprint: str | None,
        provider: str | None,
        assignment: AIRoleAssignment | None,
        model_entry: AIModelCatalogEntry | None,
        prompt_template: AIPromptTemplate | None,
    ) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "task_type": request.task_type,
            "operation": request.operation,
            "creator_id": request.creator_id,
            "project_id": request.project_id,
            "model_role": request.model_role,
            "provider": provider,
            "model_catalog_id": getattr(model_entry, "id", None),
            "model_id": getattr(model_entry, "model_id", None),
            "model_version": getattr(model_entry, "snapshot_or_version", None),
            "template_key": getattr(prompt_template, "template_key", None),
            "template_version": getattr(prompt_template, "version", None),
            "privacy_class": request.privacy_class,
            "quality_level": request.quality_level,
            "request_fingerprint": request_hash,
            "context_fingerprint": context_fingerprint,
            "cache_policy": request.cache_policy,
            "fallback_policy": request.fallback_policy,
            "approval_policy": request.approval_policy,
            "privacy_decision": privacy.to_dict(),
            "budget": request.budget,
            "metadata_keys": sorted(request.metadata.keys()),
            "metadata_present": bool(request.metadata),
        }

    def _current_cost_totals(
        self,
        *,
        request: AIExecutionRequest,
        provider_name: str,
        now: datetime | None = None,
    ) -> tuple[float, float]:
        now = now or datetime.now(timezone.utc)
        current_month = 0.0
        current_task = 0.0
        for execution in self.repository.list_executions(creator_id=request.creator_id, provider=provider_name, limit=1000):
            if execution.created_at is None:
                continue
            try:
                created_at = datetime.fromisoformat(execution.created_at.replace("Z", "+00:00"))
            except Exception:
                continue
            if created_at.year != now.year or created_at.month != now.month:
                continue
            usage_records = self.repository.list_usage_records(execution.execution_uuid)
            execution_cost = sum(record.calculated_cost for record in usage_records)
            current_month += execution_cost
            if execution.task_type == request.task_type and execution.operation == request.operation:
                current_task += execution_cost
        return current_month, current_task

    def _duplicate_execution(
        self,
        *,
        request: AIExecutionRequest,
        request_hash: str,
        provider_name: str,
    ) -> AIExecutionRecord | None:
        execution = self.repository.find_execution_by_request_id(request.request_id)
        if execution is not None and execution.status in _ACTIVE_EXECUTION_STATUSES:
            return execution
        execution = self.repository.get_execution_by_request_fingerprint(request_hash)
        if execution is not None and execution.status in _ACTIVE_EXECUTION_STATUSES:
            return execution
        return None

    def _request_fingerprint(self, request: AIExecutionRequest) -> str:
        payload = request.to_dict()
        payload.pop("request_id", None)
        payload.pop("cache_policy", None)
        payload.pop("fallback_policy", None)
        payload.pop("approval_policy", None)
        return build_request_fingerprint(payload)

    def run_diagnostic(
        self,
        *,
        provider: str | None = None,
        role: str | None = None,
        request_id: str | None = None,
        creator_id: str | None = None,
        project_id: str | None = None,
        cache_policy: str = "use",
        fallback_policy: str = "none",
        approval_policy: str = "not_required",
        privacy_class: str = "selected_text_allowed",
        metadata: dict[str, object] | None = None,
    ) -> AIExecutionResult:
        request = AIExecutionRequest(
            request_id=request_id or f"provider_diagnostic:{provider or 'any'}:{role or 'cheap_structured_model'}:{uuid4()}",
            task_type="provider_diagnostic",
            operation="extract",
            creator_id=creator_id,
            project_id=project_id,
            model_role=role,
            quality_level="standard",
            privacy_class=privacy_class,
            input_data={"status": "ok", "logical_role": role or "cheap_structured_model", "short_message": "Provider diagnostic request."},
            context_package={},
            output_contract={"required": ["status", "logical_role", "short_message"]},
            budget={"provider": provider},
            cache_policy=cache_policy,
            fallback_policy=fallback_policy,
            approval_policy=approval_policy,
            metadata=metadata or {},
        )
        logger.info(
            "ai_runtime_diagnostic.execution_created request_id=%s provider=%s role=%s cache_policy=%s",
            request.request_id,
            provider or "auto",
            role or "cheap_structured_model",
            cache_policy,
        )
        return self.run(request, provider=provider)

    def run(self, request: AIExecutionRequest, *, provider: str | None = None) -> AIExecutionResult:
        privacy = self.privacy_policy.evaluate(request)
        request_hash = self._request_fingerprint(request)
        context_fingerprint = build_request_fingerprint(request.context_package) if request.context_package else None
        prompt_template = self.prompt_registry.get_approved("provider_diagnostic")
        execution_uuid = str(uuid4())
        now = _utc_now()

        if request.task_type != "provider_diagnostic":
            error = AIExecutionError(
                category="invalid_request",
                safe_message="Only provider_diagnostic is supported in this foundation.",
                suggested_action="Use provider_diagnostic.",
            )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="blocked_by_model",
                provider=provider,
                prompt_template=prompt_template,
                context_fingerprint=context_fingerprint,
            )

        if privacy.decision == "blocked":
            error = AIExecutionError(
                category="privacy_block",
                safe_message="Request blocked by privacy policy.",
                suggested_action="Reduce sensitivity or approval requirements.",
            )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="blocked_by_privacy",
                provider=provider,
                prompt_template=prompt_template,
                context_fingerprint=context_fingerprint,
            )

        resolved = self._resolve_target(request, provider)
        if resolved is None:
            error = AIExecutionError(
                category="model_unavailable",
                safe_message="No enabled model assignment is available for the requested role.",
                suggested_action="Assign a model to the role first.",
            )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="blocked_by_model",
                provider=provider,
                prompt_template=prompt_template,
                context_fingerprint=context_fingerprint,
            )

        assignment, model_entry = resolved
        provider_name = assignment.provider
        if not self._provider_enabled(provider_name):
            error = AIExecutionError(
                category="provider_error",
                safe_message=f"Provider '{provider_name}' is disabled by runtime policy.",
                suggested_action="Enable the provider in runtime settings.",
            )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="blocked_by_provider",
                provider=provider_name,
                prompt_template=prompt_template,
                assignment=assignment,
                model_entry=model_entry,
                context_fingerprint=context_fingerprint,
            )

        duplicate_execution = self._duplicate_execution(
            request=request,
            request_hash=request_hash,
            provider_name=provider_name,
        )
        if duplicate_execution is not None:
            error = AIExecutionError(
                category="internal_error",
                safe_message="A matching execution is already in progress.",
                suggested_action="Wait for the current execution to finish.",
            )
            if duplicate_execution.request_fingerprint == request_hash:
                now = _utc_now()
                return AIExecutionResult(
                    execution_id=execution_uuid,
                    request_id=request.request_id,
                    status="queued",
                    provider=provider_name,
                    model_id=model_entry.model_id,
                    model_version=model_entry.snapshot_or_version,
                    model_role=assignment.role,
                    result=None,
                    structured_output=None,
                    validation=AIExecutionValidation(status="rejected", schema_name=request.task_type, issues=(error.safe_message,), warnings=()),
                    usage=AIExecutionUsage(),
                    cost=AICostSummary(None, None, currency="USD", notes="Duplicate active request fingerprint blocked before provider call."),
                    latency=AIExecutionLatency(latency_ms=0, started_at=now, completed_at=now, attempts=1),
                    cache=AIExecutionCacheInfo(cache_status="invalidated"),
                    fallback={"used": False, "policy": request.fallback_policy, "duplicate_of": duplicate_execution.execution_uuid},
                    warnings=(),
                    error=error,
                    provenance={"request_fingerprint": request_hash, "context_fingerprint": context_fingerprint, "duplicate_of": duplicate_execution.execution_uuid},
                    timestamps={"created_at": now, "started_at": now, "completed_at": now},
                )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="queued",
                provider=provider_name,
                prompt_template=prompt_template,
                assignment=assignment,
                model_entry=model_entry,
                context_fingerprint=context_fingerprint,
            )

        provider_client = self.providers.get(provider_name)
        if provider_client is None:
            error = AIExecutionError(
                category="provider_error",
                safe_message=f"Provider '{provider_name}' is not configured in the orchestrator.",
                suggested_action="Register the provider adapter.",
            )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="blocked_by_provider",
                provider=provider_name,
                prompt_template=prompt_template,
                assignment=assignment,
                model_entry=model_entry,
                context_fingerprint=context_fingerprint,
            )

        api_key = self.credential_store.load(CredentialStore.reference_for_provider(provider_name))
        if not api_key:
            error = AIExecutionError(
                category="authentication_error",
                safe_message=f"Credential missing for provider '{provider_name}'.",
                suggested_action="Store the provider API key.",
                technical_reference=CredentialStore.reference_for_provider(provider_name),
            )
            return self._blocked_result(
                request=request,
                execution_uuid=execution_uuid,
                request_hash=request_hash,
                privacy=privacy,
                error=error,
                status="blocked_by_credentials",
                provider=provider_name,
                prompt_template=prompt_template,
                assignment=assignment,
                model_entry=model_entry,
                context_fingerprint=context_fingerprint,
            )

        prompt_text = self._render_prompt(prompt_template, request)
        cache_key = self._cache_key(
            provider_name=provider_name,
            model_entry=model_entry,
            template=prompt_template,
            request=request,
            request_fingerprint=request_hash,
            context_fingerprint=context_fingerprint,
        )
        if request.cache_policy == "use":
            lookup = self.cache.get(cache_key)
            if lookup.hit and lookup.entry is not None:
                cached_execution = self.repository.get_execution_by_uuid(lookup.entry.result_reference)
                if cached_execution is not None:
                    return self._cached_result(
                        request=request,
                        execution_uuid=execution_uuid,
                        request_hash=request_hash,
                        context_fingerprint=context_fingerprint,
                        privacy=privacy,
                        assignment=assignment,
                        model_entry=model_entry,
                        prompt_template=prompt_template,
                        cache_entry=lookup.entry,
                        cached_execution=cached_execution,
                    )
        if request.cache_policy == "refresh":
            self.cache.invalidate(cache_key)

        estimate = self.cost_estimator.estimate(
            model_entry,
            input_tokens=max(8, len(prompt_text.split())),
            output_tokens=32,
            cached_input_tokens=0,
        )
        budget_policy = self.repository.get_budget_policy(request.creator_id, provider_name)
        budget_decision = None
        current_month_cost = 0.0
        current_task_cost = 0.0
        if budget_policy is not None:
            current_month_cost, current_task_cost = self._current_cost_totals(
                request=request,
                provider_name=provider_name,
            )
            budget_decision = BudgetPolicy(policy=budget_policy).evaluate(
                request,
                estimated_cost=estimate.maximum_cost if estimate.maximum_cost is not None else estimate.minimum_cost,
                current_month_cost=current_month_cost,
                current_task_cost=current_task_cost,
            )
            if budget_decision.blocked:
                error = AIExecutionError(
                    category="budget_block",
                    safe_message="Request blocked by budget policy.",
                    suggested_action="Increase budget or reduce scope.",
                    technical_reference="budget_policy",
                )
                return self._blocked_result(
                    request=request,
                    execution_uuid=execution_uuid,
                    request_hash=request_hash,
                    privacy=privacy,
                    error=error,
                    status="blocked_by_budget",
                    provider=provider_name,
                    prompt_template=prompt_template,
                    assignment=assignment,
                    model_entry=model_entry,
                    context_fingerprint=context_fingerprint,
                )
            if budget_decision.approval_required:
                error = AIExecutionError(
                    category="budget_block",
                    safe_message="Execution requires approval because the budget policy needs review.",
                    suggested_action="Approve the execution or reduce the estimated cost.",
                    technical_reference="budget_policy",
                )
                return self._blocked_result(
                    request=request,
                    execution_uuid=execution_uuid,
                    request_hash=request_hash,
                    privacy=privacy,
                    error=error,
                    status="awaiting_approval",
                    provider=provider_name,
                    prompt_template=prompt_template,
                    assignment=assignment,
                    model_entry=model_entry,
                    context_fingerprint=context_fingerprint,
                )

        if request.cache_policy == "refresh":
            self.cache.invalidate(cache_key)

        execution_record = self.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=execution_uuid,
                creator_id=request.creator_id,
                project_id=request.project_id,
                task_type=request.task_type,
                operation=request.operation,
                status="running",
                requested_model_role=assignment.role,
                provider=provider_name,
                model_catalog_id=model_entry.id,
                template_id=prompt_template.id if prompt_template else None,
                privacy_class=request.privacy_class,
                quality_level=request.quality_level,
                context_fingerprint=context_fingerprint,
                request_fingerprint=request_hash,
                input_summary_json=self._request_summary(
                    request=request,
                    privacy=privacy,
                    request_hash=request_hash,
                    context_fingerprint=context_fingerprint,
                    provider=provider_name,
                    assignment=assignment,
                    model_entry=model_entry,
                    prompt_template=prompt_template,
                ),
                output_reference=None,
                validation_status=None,
                cache_status="active",
                fallback_policy=request.fallback_policy,
                approval_required=privacy.approval_required,
                approved_at=None if privacy.approval_required else now,
                started_at=now,
                completed_at=None,
                latency_ms=None,
                error_category=None,
                error_code=None,
                error_message_safe=None,
                created_at=now,
                updated_at=now,
            )
        )

        logger.info(
            "ai_runtime_diagnostic.provider_call_started execution_uuid=%s provider=%s model_id=%s role=%s",
            execution_uuid,
            provider_name,
            model_entry.model_id,
            assignment.role,
        )
        response, attempts = self._execute_with_retry(provider_client, request, api_key, model_entry.model_id, prompt_text)
        logger.info(
            "ai_runtime_diagnostic.provider_call_completed execution_uuid=%s provider=%s model_id=%s attempts=%s error=%s",
            execution_uuid,
            provider_name,
            model_entry.model_id,
            attempts,
            response.error.category if response.error is not None else "none",
        )
        if response.error is not None:
            error = response.error
            self.repository.store_execution(
                replace(
                    execution_record,
                    status="failed",
                    completed_at=_utc_now(),
                    latency_ms=response.latency_ms,
                    error_category=error.category,
                    error_code=error.provider_code,
                    error_message_safe=error.safe_message,
                    updated_at=_utc_now(),
                )
            )
            return AIExecutionResult(
                execution_id=execution_uuid,
                request_id=request.request_id,
                status="failed",
                provider=provider_name,
                model_id=model_entry.model_id,
                model_version=response.model_version or model_entry.snapshot_or_version,
                model_role=assignment.role,
                result=response.output_text or None,
                structured_output=response.structured_output,
                validation=AIExecutionValidation(status="rejected", schema_name=request.task_type, issues=(error.safe_message,), warnings=()),
                usage=response.usage,
                cost=self._cost_summary(estimate, response.usage),
                latency=AIExecutionLatency(latency_ms=response.latency_ms, started_at=execution_record.started_at, completed_at=_utc_now(), attempts=attempts),
                cache=AIExecutionCacheInfo(cache_status="active", cache_key=cache_key, hit_count=0, refresh_requested=request.cache_policy == "refresh"),
                fallback={"used": False, "policy": request.fallback_policy, "attempts": attempts},
                warnings=response.warnings,
                error=error,
                provenance={"request_fingerprint": request_hash, "context_fingerprint": context_fingerprint, "provider": provider_name},
                timestamps={"created_at": execution_record.created_at, "started_at": execution_record.started_at, "completed_at": _utc_now()},
            )

        payload_object = response.structured_output or self._safe_parse(response.output_text)
        logger.info("ai_runtime_diagnostic.validation_started execution_uuid=%s", execution_uuid)
        validation = self.result_validator.validate(request=request, payload=payload_object or {}, output_text=response.output_text)
        if validation.status == "rejected":
            repaired = self.result_validator.repair(response.output_text)
            if repaired is not None:
                repaired_object = self._safe_parse(repaired)
                if repaired_object is not None:
                    validation = self.result_validator.validate(request=request, payload=repaired_object, output_text=repaired)
                    if validation.status != "rejected":
                        response = replace(response, output_text=repaired, structured_output=repaired_object)
                        payload_object = repaired_object

        usage = self.cost_tracker.record_usage(
            AIExecutionUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cached_input_tokens=response.usage.cached_input_tokens,
                reasoning_tokens=response.usage.reasoning_tokens,
                provider_reported_cost=response.usage.provider_reported_cost,
                calculated_cost=self._cost_summary(estimate, response.usage).calculated_cost or 0.0,
                currency=estimate.currency,
                pricing_version=estimate.pricing_version,
                calculation_notes="Calculated locally from catalog pricing.",
            )
        )
        cost = self._cost_summary(estimate, usage)
        latency = AIExecutionLatency(latency_ms=response.latency_ms, started_at=execution_record.started_at, completed_at=_utc_now(), attempts=attempts)
        result = AIExecutionResult(
            execution_id=execution_uuid,
            request_id=request.request_id,
            status="completed" if validation.status == "valid" else "completed_with_warnings",
            provider=provider_name,
            model_id=model_entry.model_id,
            model_version=response.model_version or model_entry.snapshot_or_version,
            model_role=assignment.role,
            result=response.output_text,
            structured_output=payload_object if isinstance(payload_object, dict) else None,
            validation=validation,
            usage=usage,
            cost=cost,
            latency=latency,
            cache=AIExecutionCacheInfo(cache_status="active", cache_key=cache_key, hit_count=0, refresh_requested=request.cache_policy == "refresh"),
            fallback={"used": False, "policy": request.fallback_policy, "attempts": attempts},
            warnings=response.warnings + validation.warnings,
            error=None,
            provenance={"provider": provider_name, "model_catalog_id": model_entry.id, "request_fingerprint": request_hash, "context_fingerprint": context_fingerprint},
            timestamps={"created_at": execution_record.created_at, "started_at": execution_record.started_at, "completed_at": latency.completed_at},
        )

        self._persist_success(
            request=request,
            execution_uuid=execution_uuid,
            execution_record=execution_record,
            provider_name=provider_name,
            assignment=assignment,
            model_entry=model_entry,
            prompt_template=prompt_template,
            request_fingerprint=request_hash,
            prompt_text=prompt_text,
            provider_response=response,
            validation=validation,
            usage=usage,
            cost=cost,
            latency=latency,
            cache_key=cache_key,
            result=result,
            privacy=privacy,
            context_fingerprint=context_fingerprint,
        )
        logger.info(
            "ai_runtime_diagnostic.execution_completed execution_uuid=%s provider=%s model_id=%s status=%s",
            execution_uuid,
            provider_name,
            model_entry.model_id,
            result.status,
        )
        return result

    def _resolve_target(self, request: AIExecutionRequest, provider: str | None) -> tuple[AIRoleAssignment, AIModelCatalogEntry] | None:
        if request.model_role is not None:
            resolved = self.model_registry.resolve_role(request.model_role, creator_id=request.creator_id, provider=provider)
            if resolved is not None:
                assignment, model = resolved
                if model.status in {"approved", "testing"}:
                    return assignment, model
            return None
        if provider is not None:
            assignments = [assignment for assignment in self.model_registry.list_roles(creator_id=request.creator_id, provider=provider) if assignment.is_enabled]
            if not assignments:
                return None
            selected = next((assignment for assignment in assignments if assignment.is_default), assignments[0])
            model = self.model_registry.get_model(selected.model_catalog_id)
            if model is not None and model.status in {"approved", "testing"}:
                return selected, model
        return None

    def _cache_key(
        self,
        *,
        provider_name: str,
        model_entry: AIModelCatalogEntry,
        template: AIPromptTemplate | None,
        request: AIExecutionRequest,
        request_fingerprint: str,
        context_fingerprint: str | None,
    ) -> str:
        template_key = template.template_key if template else "provider_diagnostic"
        template_version = template.version if template else None
        model_version = model_entry.snapshot_or_version
        fingerprint = build_request_fingerprint(
            {
                "task_type": request.task_type,
                "operation": request.operation,
                "provider": provider_name,
                "model_id": model_entry.model_id,
                "model_version": model_version,
                "template_key": template_key,
                "template_version": template_version,
                "request_fingerprint": request_fingerprint,
                "context_fingerprint": context_fingerprint,
                "quality_level": request.quality_level,
                "privacy_class": request.privacy_class,
                "cache_policy": request.cache_policy,
                "fallback_policy": request.fallback_policy,
                "approval_policy": request.approval_policy,
                "budget": request.budget,
                "metadata": request.metadata,
            }
        )
        return f"ai:{provider_name}:{model_entry.model_id}:{template_key}:{template_version or 'none'}:{model_version or 'none'}:{fingerprint}"

    def _render_prompt(self, template: AIPromptTemplate | None, request: AIExecutionRequest) -> str:
        payload = {
            "status": "ok",
            "logical_role": request.model_role or "cheap_structured_model",
            "short_message": "Provider diagnostic completed successfully.",
        }
        if template and template.instruction_layers_json:
            payload["instruction_layers"] = template.instruction_layers_json
        return json.dumps(payload, ensure_ascii=False)

    def _safe_parse(self, text: str | None) -> dict[str, object] | None:
        if not text:
            return None
        try:
            value = json.loads(text)
        except Exception:
            return None
        return value if isinstance(value, dict) else None

    def _execute_with_retry(self, provider_client: AIProvider, request: AIExecutionRequest, api_key: str, model_id: str, prompt_text: str) -> tuple[AIProviderResponse, int]:
        attempts = 0
        last_response: AIProviderResponse | None = None
        while attempts <= self.max_retries:
            attempts += 1
            response = provider_client.execute(request, api_key=api_key, model_id=model_id, prompt_text=prompt_text)
            last_response = response
            if response.error is None:
                return response, attempts
            if response.error.category not in {"timeout", "network_error", "rate_limit_error", "provider_error"}:
                break
        assert last_response is not None
        return last_response, attempts

    def _cost_summary(self, estimate, usage: AIExecutionUsage) -> AICostSummary:
        return AICostSummary(
            estimated_min_cost=estimate.minimum_cost,
            estimated_max_cost=estimate.maximum_cost,
            calculated_cost=usage.calculated_cost,
            provider_reported_cost=usage.provider_reported_cost,
            currency=usage.currency,
            pricing_version=usage.pricing_version,
            notes=estimate.notes,
        )

    def _blocked_result(
        self,
        *,
        request: AIExecutionRequest,
        execution_uuid: str,
        request_hash: str,
        privacy,
        error: AIExecutionError,
        status: str,
        provider: str | None,
        prompt_template: AIPromptTemplate | None,
        assignment: AIRoleAssignment | None = None,
        model_entry: AIModelCatalogEntry | None = None,
        context_fingerprint: str | None = None,
    ) -> AIExecutionResult:
        now = _utc_now()
        self.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=execution_uuid,
                creator_id=request.creator_id,
                project_id=request.project_id,
                task_type=request.task_type,
                operation=request.operation,
                status=status,
                requested_model_role=assignment.role if assignment else request.model_role,
                provider=provider,
                model_catalog_id=getattr(model_entry, "id", None),
                template_id=prompt_template.id if prompt_template else None,
                privacy_class=request.privacy_class,
                quality_level=request.quality_level,
                context_fingerprint=context_fingerprint,
                request_fingerprint=request_hash,
                input_summary_json=self._request_summary(
                    request=request,
                    privacy=privacy,
                    request_hash=request_hash,
                    context_fingerprint=context_fingerprint,
                    provider=provider,
                    assignment=assignment,
                    model_entry=model_entry,
                    prompt_template=prompt_template,
                ),
                output_reference=None,
                validation_status=None,
                cache_status="invalidated",
                fallback_policy=request.fallback_policy,
                approval_required=privacy.approval_required,
                approved_at=None,
                started_at=now,
                completed_at=now,
                latency_ms=0,
                error_category=error.category,
                error_code=error.provider_code,
                error_message_safe=error.safe_message,
                created_at=now,
                updated_at=now,
            )
        )
        return AIExecutionResult(
            execution_id=execution_uuid,
            request_id=request.request_id,
            status=status,
            provider=provider,
            model_id=getattr(model_entry, "model_id", None),
            model_version=getattr(model_entry, "snapshot_or_version", None),
            model_role=assignment.role if assignment else request.model_role,
            result=None,
            structured_output=None,
            validation=AIExecutionValidation(status="rejected", schema_name=request.task_type, issues=(error.safe_message,), warnings=()),
            usage=AIExecutionUsage(),
            cost=AICostSummary(None, None, currency="USD", notes="Execution was blocked before provider call."),
            latency=AIExecutionLatency(latency_ms=0, started_at=now, completed_at=now, attempts=1),
            cache=AIExecutionCacheInfo(cache_status="invalidated"),
            fallback={"used": False, "policy": request.fallback_policy},
            warnings=(),
            error=error,
            provenance={"request_fingerprint": request_hash, "context_fingerprint": context_fingerprint},
            timestamps={"created_at": now, "started_at": now, "completed_at": now},
        )

    def _persist_success(
        self,
        *,
        request: AIExecutionRequest,
        execution_uuid: str,
        execution_record: AIExecutionRecord,
        provider_name: str,
        assignment: AIRoleAssignment,
        model_entry: AIModelCatalogEntry,
        prompt_template: AIPromptTemplate | None,
        request_fingerprint: str,
        prompt_text: str,
        provider_response: AIProviderResponse,
        validation: AIExecutionValidation,
        usage: AIExecutionUsage,
        cost,
        latency: AIExecutionLatency,
        cache_key: str,
        result: AIExecutionResult,
        privacy,
        context_fingerprint: str | None,
    ) -> None:
        now = _utc_now()
        output_json = provider_response.structured_output or self._safe_parse(provider_response.output_text)
        request_summary = self._request_summary(
            request=request,
            privacy=privacy,
            request_hash=request_fingerprint,
            context_fingerprint=context_fingerprint,
            provider=provider_name,
            assignment=assignment,
            model_entry=model_entry,
            prompt_template=prompt_template,
        )
        redacted = privacy.decision != "allowed"
        self.repository.store_payload(
            AIExecutionPayload(
                execution_id=execution_uuid,
                payload_type="prepared_request",
                content_json={"request_summary": request_summary, "prompt": prompt_text if not redacted else "[redacted]"},
                content_text=prompt_text if not redacted else "[redacted]",
                content_hash=request_fingerprint,
                is_redacted=redacted,
                retention_class="diagnostic",
                created_at=now,
            )
        )
        self.repository.store_payload(
            AIExecutionPayload(
                execution_id=execution_uuid,
                payload_type="provider_response",
                content_json=output_json if not redacted else {"status": "redacted"},
                content_text=provider_response.output_text if not redacted else "[redacted]",
                content_hash=request_fingerprint,
                is_redacted=redacted,
                retention_class="diagnostic",
                created_at=now,
            )
        )
        self.repository.store_payload(
            AIExecutionPayload(
                execution_id=execution_uuid,
                payload_type="validated_result",
                content_json=result.structured_output if not redacted else {"status": "redacted"},
                content_text=result.result if not redacted else "[redacted]",
                content_hash=request_fingerprint,
                is_redacted=redacted,
                retention_class="diagnostic",
                created_at=now,
            )
        )
        self.repository.store_payload(
            AIExecutionPayload(
                execution_id=execution_uuid,
                payload_type="validation_report",
                content_json=validation.to_dict(),
                content_text=validation.status,
                content_hash=request_fingerprint,
                is_redacted=False,
                retention_class="diagnostic",
                created_at=now,
            )
        )
        self.repository.store_usage(
            AIUsageRecord(
                execution_id=execution_uuid,
                provider=provider_name,
                model_catalog_id=model_entry.id,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
                reasoning_tokens=usage.reasoning_tokens,
                provider_reported_cost=usage.provider_reported_cost,
                calculated_cost=usage.calculated_cost,
                currency=usage.currency,
                pricing_version=usage.pricing_version,
                calculation_notes=usage.calculation_notes,
                created_at=now,
            )
        )
        self.repository.store_execution(
            replace(
                execution_record,
                status=result.status,
                output_reference=f"{execution_uuid}:validated_result",
                validation_status=validation.status,
                cache_status=result.cache.cache_status,
                completed_at=latency.completed_at,
                latency_ms=latency.latency_ms,
                error_category=None,
                error_code=None,
                error_message_safe=None,
                updated_at=now,
            )
        )
        self.cache.put(
            AICacheEntry(
                cache_key=cache_key,
                task_type=request.task_type,
                operation=request.operation,
                provider=provider_name,
                model_catalog_id=model_entry.id,
                template_id=prompt_template.id if prompt_template else None,
                request_fingerprint=request_fingerprint,
                context_fingerprint=context_fingerprint,
                result_reference=execution_uuid,
                status="active",
                created_at=now,
                expires_at=None,
                last_accessed_at=now,
                hit_count=0,
            )
        )

    def _cached_result(
        self,
        *,
        request: AIExecutionRequest,
        execution_uuid: str,
        request_hash: str,
        context_fingerprint: str | None,
        privacy,
        assignment: AIRoleAssignment,
        model_entry: AIModelCatalogEntry,
        prompt_template: AIPromptTemplate | None,
        cache_entry: AICacheEntry,
        cached_execution: AIExecutionRecord,
    ) -> AIExecutionResult:
        payloads = self.repository.list_payloads(cached_execution.execution_uuid)
        validated = next((payload for payload in payloads if payload.payload_type == "validated_result"), None)
        report = next((payload for payload in payloads if payload.payload_type == "validation_report"), None)
        validation = AIExecutionValidation(status=cached_execution.validation_status or "valid", schema_name=request.task_type, issues=(), warnings=())
        if report and report.content_json:
            validation = AIExecutionValidation(
                status=report.content_json.get("status", validation.status),
                schema_name=report.content_json.get("schema_name", request.task_type),
                issues=tuple(report.content_json.get("issues") or ()),
                warnings=tuple(report.content_json.get("warnings") or ()),
            )
        now = _utc_now()
        return AIExecutionResult(
            execution_id=execution_uuid,
            request_id=request.request_id,
            status=cached_execution.status if cached_execution.status in {"completed", "completed_with_warnings"} else "completed",
            provider=assignment.provider,
            model_id=model_entry.model_id,
            model_version=getattr(model_entry, "snapshot_or_version", None),
            model_role=assignment.role,
            result=validated.content_text if validated else None,
            structured_output=validated.content_json if validated else None,
            validation=validation,
            usage=AIExecutionUsage(),
            cost=AICostSummary(0.0, 0.0, calculated_cost=0.0, provider_reported_cost=None, currency="USD", notes="Returned from cache."),
            latency=AIExecutionLatency(latency_ms=0, started_at=now, completed_at=now, attempts=1),
            cache=AIExecutionCacheInfo(cache_status="exact_hit", cache_key=cache_entry.cache_key, hit_count=cache_entry.hit_count + 1, refresh_requested=False),
            fallback={"used": False, "policy": request.fallback_policy, "cached_from": cached_execution.execution_uuid},
            warnings=(),
            error=None,
            provenance={"request_fingerprint": request_hash, "context_fingerprint": context_fingerprint, "cached_from": cached_execution.execution_uuid},
            timestamps={"created_at": now, "started_at": now, "completed_at": now},
        )
