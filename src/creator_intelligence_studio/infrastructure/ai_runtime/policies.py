"""Policies and validation for the AI runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import (
    AIBudgetDecision,
    AIBudgetPolicy,
    AICostEstimate,
    AIErrorCategory,
    AIExecutionError,
    AIExecutionRequest,
    AIExecutionUsage,
    AIExecutionValidation,
    AIExecutionValidationStatus,
    AIPrivacyDecision,
    AIPrivacyDecisionStatus,
    AIProviderResponse,
    AIQualityLevel,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class PrivacyPolicyEngine:
    allowed_providers: tuple[str, ...] = ("openai", "anthropic")

    def evaluate(self, request: AIExecutionRequest) -> AIPrivacyDecision:
        if request.privacy_class == "local_only":
            return AIPrivacyDecision(
                decision="blocked",
                allowed_providers=(),
                allowed_modalities=("local",),
                redactions_required=(),
                approval_required=True,
                reasons=("local_only requests cannot leave the device.",),
                blocked_fields=("all",),
            )
        if request.privacy_class == "blocked_external":
            return AIPrivacyDecision(
                decision="blocked",
                allowed_providers=(),
                allowed_modalities=(),
                redactions_required=(),
                approval_required=True,
                reasons=("External providers are blocked for this request.",),
                blocked_fields=("all",),
            )
        allowed_modalities = ("text",)
        if request.privacy_class == "selected_images_allowed":
            allowed_modalities = ("text", "image")
        elif request.privacy_class == "selected_audio_allowed":
            allowed_modalities = ("text", "audio")
        reasons = ["Request is allowed after local review."]
        decision = "allowed"
        redactions: tuple[str, ...] = ()
        approval_required = request.approval_policy in {"required_before_execution", "required_before_cross_provider"}
        if request.privacy_class in {"selected_text_allowed", "selected_images_allowed", "selected_audio_allowed"}:
            decision = "allowed_with_redaction"
            redactions = ("sensitive_fields",)
        return AIPrivacyDecision(
            decision=decision,
            allowed_providers=self.allowed_providers,
            allowed_modalities=allowed_modalities,
            redactions_required=redactions,
            approval_required=approval_required,
            reasons=tuple(reasons),
            blocked_fields=(),
        )


@dataclass(frozen=True, slots=True)
class BudgetPolicy:
    policy: AIBudgetPolicy | None = None

    def evaluate(self, request: AIExecutionRequest, *, estimated_cost: float | None, current_month_cost: float | None = None, current_task_cost: float | None = None) -> AIBudgetDecision:
        policy = self.policy or AIBudgetPolicy()
        reasons: list[str] = []
        blocked = False
        approval_required = False
        if estimated_cost is None:
            approval_required = True
            reasons.append("Pricing is unavailable.")
        if policy.monthly_limit is not None and estimated_cost is not None:
            projected_month = (current_month_cost or 0.0) + estimated_cost
            if projected_month > policy.monthly_limit:
                if policy.hard_block_enabled:
                    blocked = True
                    reasons.append("Monthly budget would be exceeded.")
                else:
                    approval_required = True
                    reasons.append("Monthly budget would be exceeded and requires approval.")
        if policy.per_task_limit is not None and estimated_cost is not None:
            projected_task = (current_task_cost or 0.0) + estimated_cost
            if projected_task > policy.per_task_limit:
                if policy.hard_block_enabled:
                    blocked = True
                    reasons.append("Task budget would be exceeded.")
                else:
                    approval_required = True
                    reasons.append("Task budget would be exceeded and requires approval.")
        if estimated_cost is not None and policy.warning_threshold_90 and policy.monthly_limit:
            if estimated_cost >= policy.monthly_limit * policy.warning_threshold_90:
                approval_required = True
                reasons.append("Estimated cost crosses the 90% warning threshold.")
        if not reasons:
            reasons.append("Budget policy allows execution.")
        return AIBudgetDecision(
            decision="blocked" if blocked else "allowed",
            reasons=tuple(reasons),
            currency=policy.currency,
            estimated_cost=estimated_cost,
            hard_block_enabled=policy.hard_block_enabled,
            warning_threshold_50=policy.warning_threshold_50,
            warning_threshold_75=policy.warning_threshold_75,
            warning_threshold_90=policy.warning_threshold_90,
            approval_required=approval_required,
            blocked=blocked,
        )


@dataclass(frozen=True, slots=True)
class CostEstimator:
    pricing_version: str = "v1"

    def estimate(self, model_entry: Any, *, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> AICostEstimate:
        currency = getattr(model_entry, "pricing_currency", None) or "USD"
        input_price = getattr(model_entry, "input_price_per_million", None)
        output_price = getattr(model_entry, "output_price_per_million", None)
        cached_price = getattr(model_entry, "cached_input_price_per_million", None)
        warnings: list[str] = []
        if input_price is None or output_price is None:
            warnings.append("Pricing not available.")
            return AICostEstimate(None, None, currency=currency, pricing_version=self.pricing_version, warnings=tuple(warnings), notes="Unknown pricing.")
        minimum = ((input_tokens - cached_input_tokens) / 1_000_000) * input_price
        maximum = minimum + (output_tokens / 1_000_000) * output_price
        if cached_input_tokens and cached_price is not None:
            minimum = ((input_tokens - cached_input_tokens) / 1_000_000) * input_price + (
                (cached_input_tokens / 1_000_000) * cached_price
            )
        return AICostEstimate(
            minimum_cost=round(max(minimum, 0.0), 8),
            maximum_cost=round(max(maximum, 0.0), 8),
            currency=currency,
            pricing_version=self.pricing_version,
            warnings=tuple(warnings),
            notes="Estimated from catalog prices.",
        )


@dataclass(frozen=True, slots=True)
class CostTracker:
    def record_usage(self, usage: AIExecutionUsage) -> AIExecutionUsage:
        return usage

    def aggregate(self, records: list[AIExecutionUsage]) -> dict[str, Any]:
        total_input = sum(item.input_tokens for item in records)
        total_output = sum(item.output_tokens for item in records)
        total_cached = sum(item.cached_input_tokens for item in records)
        total_cost = sum((item.calculated_cost or 0.0) for item in records)
        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cached_input_tokens": total_cached,
            "calculated_cost": round(total_cost, 8),
        }


def _normalize_textual_diagnostic_output(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.startswith("```") and stripped.endswith("```"):
        inner = stripped[3:-3].strip()
        first_newline = inner.find("\n")
        if first_newline >= 0:
            inner = inner[first_newline + 1 :].strip()
        stripped = inner
    stripped = stripped.strip(" \t\r\n`")
    while stripped and stripped[0] in "\"'":
        stripped = stripped[1:].lstrip()
    while stripped and stripped[-1] in "\"'":
        stripped = stripped[:-1].rstrip()
    while stripped and stripped[-1] in ".!?,":
        stripped = stripped[:-1].rstrip()
    return stripped


def _expected_textual_diagnostic_tokens(request: AIExecutionRequest) -> tuple[str, ...]:
    tokens: list[str] = []
    for source in (request.output_contract, request.metadata):
        if not isinstance(source, dict):
            continue
        expected_text = source.get("expected_text")
        if isinstance(expected_text, str) and expected_text.strip():
            tokens.append(_normalize_textual_diagnostic_output(expected_text).lower())
        accepted_texts = source.get("accepted_texts")
        if isinstance(accepted_texts, list):
            for item in accepted_texts:
                if isinstance(item, str) and item.strip():
                    tokens.append(_normalize_textual_diagnostic_output(item).lower())
    return tuple(token for token in tokens if token)


@dataclass(frozen=True, slots=True)
class AIResultValidator:
    forbidden_terms: tuple[str, ...] = ("hack", "password", "secret", "token")

    def validate(
        self,
        *,
        request: AIExecutionRequest,
        payload: Any,
        output_text: str | None = None,
        response_state: str | None = None,
        response_status: str | None = None,
        incomplete_reason: str | None = None,
        output_token_limit: int | None = None,
    ) -> AIExecutionValidation:
        issues: list[str] = []
        warnings: list[str] = []
        normalized_text = _normalize_textual_diagnostic_output(output_text or "")
        lower_text = normalized_text.lower()
        normalized_status = (response_status or "").strip().lower()
        normalized_reason = (incomplete_reason or "").strip().lower()
        if normalized_status == "incomplete" or response_state == "truncated":
            issues.append("Response was truncated.")
            if output_token_limit is not None:
                warnings.append(f"output_token_limit:{output_token_limit}")
            if normalized_reason:
                warnings.append(f"incomplete_reason:{normalized_reason}")
        if response_state in {"refusal", "content_filter"}:
            issues.append(f"Response state is {response_state}.")
        elif response_state == "empty" and not normalized_text:
            issues.append("Response text is empty.")
        if normalized_status == "completed" and not normalized_text:
            issues.append("Output text is empty.")

        if isinstance(payload, dict):
            required = {"status", "logical_role", "short_message"}
            missing = sorted(required - set(payload))
            if missing:
                issues.append(f"Missing keys: {', '.join(missing)}.")
            if payload.get("status") != "ok":
                warnings.append("Status is not ok.")
            short_message = payload.get("short_message")
            if not isinstance(short_message, str) or not short_message.strip():
                issues.append("short_message must be a non-empty string.")
            elif len(short_message.strip()) > 280:
                issues.append("short_message is too long.")
            text = output_text or ""
            if not text and payload:
                try:
                    text = json.dumps(payload, ensure_ascii=False)
                except Exception:
                    text = ""
            lowered = text.lower()
        else:
            if not normalized_text:
                issues.append("Output text is empty.")
            expected_tokens = _expected_textual_diagnostic_tokens(request)
            if expected_tokens:
                normalized_candidate = lower_text
                if normalized_candidate not in expected_tokens:
                    issues.append("Output text does not match the expected diagnostic response.")
            lowered = lower_text

        forbidden = [term for term in self.forbidden_terms if term in lowered]
        if forbidden:
            issues.append(f"Forbidden terms present: {', '.join(forbidden)}.")
        if issues:
            return AIExecutionValidation(status="rejected", schema_name=request.task_type, issues=tuple(issues), warnings=tuple(warnings))
        if warnings:
            return AIExecutionValidation(status="valid_with_warnings", schema_name=request.task_type, issues=(), warnings=tuple(warnings))
        return AIExecutionValidation(status="valid", schema_name=request.task_type, issues=(), warnings=())

    def repair(self, text: str) -> str | None:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return stripped[start : end + 1]
        return None
