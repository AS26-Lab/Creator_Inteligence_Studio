"""Canonical runtime models for AI orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
import json
from typing import Any


AIProviderName = str
AIRoleName = str
AIQualityLevel = str
AIPrivacyClass = str
AICachePolicy = str
AIFallbackPolicy = str
AIApprovalPolicy = str

AIExecutionStatus = str
AIExecutionValidationStatus = str
AIProviderDiagnosticStatus = str
AIPrivacyDecisionStatus = str
AICacheStatus = str
AIModelStatus = str
AIPromptTemplateStatus = str
AIErrorCategory = str
AICredentialStatus = str


AI_EXECUTION_STATUSES = (
    "queued",
    "preparing_context",
    "awaiting_approval",
    "running",
    "validating",
    "completed",
    "completed_with_warnings",
    "failed",
    "cancelled",
    "blocked_by_budget",
    "blocked_by_privacy",
    "blocked_by_credentials",
    "blocked_by_provider",
    "blocked_by_model",
)

AI_VALIDATION_STATUSES = ("valid", "valid_with_warnings", "repairable", "requires_human_review", "rejected")
AI_PRIVACY_DECISIONS = ("allowed", "allowed_with_redaction", "requires_approval", "blocked")
AI_CACHE_STATUSES = ("active", "stale", "invalidated", "expired")
AI_MODEL_STATUSES = ("testing", "approved", "deprecated", "unavailable", "blocked")
AI_TEMPLATE_STATUSES = ("draft", "testing", "approved", "deprecated", "retired")
AI_ERROR_CATEGORIES = (
    "authentication_error",
    "authorization_error",
    "billing_error",
    "rate_limit_error",
    "quota_error",
    "model_unavailable",
    "model_deprecated",
    "invalid_request",
    "invalid_response",
    "schema_validation_error",
    "privacy_block",
    "budget_block",
    "timeout",
    "network_error",
    "provider_error",
    "cancelled_by_user",
    "internal_error",
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_request_fingerprint(payload: Any) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _to_dict(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_dict(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {key: _to_dict(item) for key, item in vars(value).items() if not key.startswith("_")}
    return value


@dataclass(frozen=True, slots=True)
class AIProviderCapabilities:
    supports_structured_output: bool = True
    supports_image_input: bool = False
    supports_audio_input: bool = False
    supports_retry: bool = True
    supports_fallback: bool = False
    modalities: tuple[str, ...] = ("text",)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIProviderDiagnostic:
    provider: AIProviderName
    configured: bool
    model_id: str | None
    status: str
    message: str
    latency_ms: int | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIProviderDiscoveredModel:
    provider: AIProviderName
    model_id: str
    display_name: str
    snapshot_or_version: str | None = None
    status: AIModelStatus = "testing"
    capabilities_json: dict[str, Any] = field(default_factory=dict)
    context_limit: int | None = None
    supports_structured_output: bool = False
    supports_image_input: bool = False
    supports_audio_input: bool = False
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None
    cached_input_price_per_million: float | None = None
    pricing_currency: str | None = "USD"
    pricing_effective_at: str | None = None
    replacement_model_id: str | None = None
    compatibility_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIProviderModelSyncReport:
    provider: AIProviderName
    status: str
    message: str
    found_count: int = 0
    compatible_count: int = 0
    new_count: int = 0
    updated_count: int = 0
    unavailable_count: int = 0
    latency_ms: int | None = None
    checked_at: str | None = None
    error: AIExecutionError | None = None
    models: tuple[AIProviderDiscoveredModel, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIModelCatalogEntry:
    provider: AIProviderName
    model_id: str
    display_name: str
    snapshot_or_version: str | None = None
    status: AIModelStatus = "testing"
    capabilities_json: dict[str, Any] = field(default_factory=dict)
    context_limit: int | None = None
    supports_structured_output: bool = True
    supports_image_input: bool = False
    supports_audio_input: bool = False
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None
    cached_input_price_per_million: float | None = None
    pricing_currency: str | None = "USD"
    pricing_effective_at: str | None = None
    last_verified_at: str | None = None
    replacement_model_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIRoleAssignment:
    role: AIRoleName
    provider: AIProviderName
    model_catalog_id: str
    creator_id: str | None = None
    quality_level: AIQualityLevel = "standard"
    is_default: bool = False
    is_enabled: bool = True
    fallback_policy: AIFallbackPolicy = "none"
    approved_benchmark_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIPromptTemplate:
    template_key: str
    task_type: str
    operation: str
    version: int
    status: AIPromptTemplateStatus = "draft"
    required_capabilities_json: dict[str, Any] = field(default_factory=dict)
    instruction_layers_json: dict[str, Any] = field(default_factory=dict)
    input_schema_json: dict[str, Any] = field(default_factory=dict)
    output_schema_json: dict[str, Any] = field(default_factory=dict)
    validation_profile_json: dict[str, Any] = field(default_factory=dict)
    benchmark_id: str | None = None
    change_notes: str | None = None
    approved_at: str | None = None
    deprecated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIBudgetPolicy:
    creator_id: str | None = None
    provider: AIProviderName | None = None
    daily_limit: float | None = None
    monthly_limit: float | None = None
    per_task_limit: float | None = None
    warning_threshold_50: float = 0.50
    warning_threshold_75: float = 0.75
    warning_threshold_90: float = 0.90
    hard_block_enabled: bool = True
    currency: str = "USD"
    effective_from: str | None = None
    effective_until: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIRuntimeSetting:
    scope_type: str
    setting_key: str
    setting_value_json: dict[str, Any]
    scope_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionRequest:
    request_id: str
    task_type: str
    operation: str
    creator_id: str | None
    project_id: str | None
    model_role: AIRoleName | None
    quality_level: AIQualityLevel
    privacy_class: AIPrivacyClass
    input_data: dict[str, Any]
    context_package: dict[str, Any]
    output_contract: dict[str, Any]
    budget: dict[str, Any]
    cache_policy: AICachePolicy
    fallback_policy: AIFallbackPolicy
    approval_policy: AIApprovalPolicy
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionError:
    category: AIErrorCategory
    safe_message: str
    provider_code: str | None = None
    retryable: bool = False
    suggested_action: str | None = None
    technical_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionValidation:
    status: AIExecutionValidationStatus
    schema_name: str | None = None
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int | None = None
    provider_reported_cost: float | None = None
    calculated_cost: float = 0.0
    currency: str = "USD"
    pricing_version: str | None = None
    calculation_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AICostSummary:
    estimated_min_cost: float | None
    estimated_max_cost: float | None
    calculated_cost: float | None = None
    provider_reported_cost: float | None = None
    currency: str = "USD"
    pricing_version: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionLatency:
    latency_ms: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionCacheInfo:
    cache_status: str
    cache_key: str | None = None
    hit_count: int = 0
    refresh_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionResult:
    execution_id: str
    request_id: str
    status: AIExecutionStatus
    provider: AIProviderName | None
    model_id: str | None
    model_version: str | None
    model_role: AIRoleName | None
    result: str | None
    structured_output: dict[str, Any] | None
    validation: AIExecutionValidation
    usage: AIExecutionUsage
    cost: AICostSummary
    latency: AIExecutionLatency
    cache: AIExecutionCacheInfo
    fallback: dict[str, Any]
    warnings: tuple[str, ...] = ()
    error: AIExecutionError | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    timestamps: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionPayload:
    execution_id: str
    payload_type: str
    content_json: dict[str, Any] | None = None
    content_text: str | None = None
    content_hash: str | None = None
    is_redacted: bool = False
    retention_class: str = "diagnostic"
    created_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIUsageRecord:
    execution_id: str
    provider: AIProviderName
    model_catalog_id: str | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int | None
    provider_reported_cost: float | None
    calculated_cost: float | None
    currency: str
    pricing_version: str | None
    calculation_notes: str | None
    created_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecutionRecord:
    execution_uuid: str
    creator_id: str | None
    project_id: str | None
    task_type: str
    operation: str
    status: AIExecutionStatus
    requested_model_role: AIRoleName | None
    provider: AIProviderName | None
    model_catalog_id: str | None
    template_id: str | None
    privacy_class: AIPrivacyClass
    quality_level: AIQualityLevel
    context_fingerprint: str | None
    request_fingerprint: str
    input_summary_json: dict[str, Any]
    output_reference: str | None
    validation_status: AIExecutionValidationStatus | None
    cache_status: AICacheStatus
    fallback_policy: AIFallbackPolicy
    approval_required: bool
    approved_at: str | None
    started_at: str | None
    completed_at: str | None
    latency_ms: int | None
    error_category: AIErrorCategory | None
    error_code: str | None
    error_message_safe: str | None
    created_at: str | None = None
    updated_at: str | None = None
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AICacheEntry:
    cache_key: str
    task_type: str
    operation: str
    provider: AIProviderName
    model_catalog_id: str | None
    template_id: str | None
    request_fingerprint: str
    context_fingerprint: str | None
    result_reference: str
    status: AICacheStatus
    created_at: str | None = None
    expires_at: str | None = None
    last_accessed_at: str | None = None
    hit_count: int = 0
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AICostEstimate:
    minimum_cost: float | None
    maximum_cost: float | None
    currency: str = "USD"
    pricing_version: str | None = None
    warnings: tuple[str, ...] = ()
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIBudgetDecision:
    decision: str
    reasons: tuple[str, ...]
    currency: str
    estimated_cost: float | None
    hard_block_enabled: bool
    warning_threshold_50: float
    warning_threshold_75: float
    warning_threshold_90: float
    approval_required: bool = False
    blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIPrivacyDecision:
    decision: AIPrivacyDecisionStatus
    allowed_providers: tuple[AIProviderName, ...]
    allowed_modalities: tuple[str, ...]
    redactions_required: tuple[str, ...]
    approval_required: bool
    reasons: tuple[str, ...]
    blocked_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIProviderResponse:
    provider: AIProviderName
    model_id: str
    model_version: str | None
    output_text: str
    structured_output: dict[str, Any] | None
    usage: AIExecutionUsage
    latency_ms: int
    content_shape: str | None = None
    content_length: int | None = None
    raw_finish_reason: str | None = None
    response_state: str | None = None
    parser_profile: str | None = None
    warnings: tuple[str, ...] = ()
    error: AIExecutionError | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AIExecution:
    execution: AIExecutionRecord
    payloads: tuple[AIExecutionPayload, ...]
    usage_records: tuple[AIUsageRecord, ...]
    cache_entry: AICacheEntry | None
    result: AIExecutionResult

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_payload(payload: Any) -> Any:
    return _to_dict(payload)
