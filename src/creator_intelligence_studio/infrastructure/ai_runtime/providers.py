"""Provider adapters for AI runtime."""

from __future__ import annotations

import json
import time
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import (
    AIErrorCategory,
    AIExecutionError,
    AIExecutionRequest,
    AIExecutionUsage,
    AIProviderCapabilities,
    AIProviderDiagnostic,
    AIProviderDiscoveredModel,
    AIProviderModelSyncReport,
    AIProviderName,
    AIProviderResponse,
)
from .request_profiles import (
    describe_openai_request_payload,
    build_openai_diagnostic_payload,
    parse_openai_chat_completions_response,
    resolve_provider_request_profile,
    validate_openai_request,
)


class AIProvider(Protocol):
    provider_name: AIProviderName

    def capabilities(self) -> AIProviderCapabilities: ...

    def test_credentials(self, api_key: str) -> AIProviderDiagnostic: ...

    def discover_models(self, api_key: str) -> AIProviderModelSyncReport: ...

    def execute(
        self,
        request: AIExecutionRequest,
        *,
        api_key: str,
        model_id: str,
        prompt_text: str,
    ) -> AIProviderResponse: ...


def _safe_error_message(message: str | None) -> str:
    if not message:
        return "Provider request failed."
    cleaned = message.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer [redacted]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"sk-[A-Za-z0-9._\-]{6,}", "[redacted]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(api[_ -]?key\s*[:=]\s*)([A-Za-z0-9._\-]{6,})", r"\1[redacted]", cleaned, flags=re.IGNORECASE)
    return cleaned[:300]


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> tuple[int, dict[str, Any] | str, int]:
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    request = Request(url, data=body, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            elapsed = int((time.perf_counter() - started) * 1000)
            if not raw:
                return response.status, {}, elapsed
            try:
                return response.status, json.loads(raw), elapsed
            except Exception:
                return response.status, raw, elapsed
    except HTTPError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        try:
            raw = exc.read().decode("utf-8")
            data: dict[str, Any] | str = json.loads(raw) if raw else {}
        except Exception:
            data = _safe_error_message(str(exc))
        return exc.code, data, elapsed
    except (TimeoutError, socket.timeout) as exc:
        raise TimeoutError(_safe_error_message(str(exc))) from exc
    except URLError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        raise ConnectionError(_safe_error_message(str(exc))) from exc


def _map_error_category(status_code: int, payload: dict[str, Any] | str) -> AIErrorCategory:
    text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else str(payload)
    lowered = text.lower()
    if "insufficient" in lowered or "credit" in lowered or "billing" in lowered or "payment" in lowered:
        return "billing_error"
    if "quota" in lowered:
        return "quota_error"
    if "deprecated" in lowered or "retired" in lowered:
        return "model_deprecated"
    if "model" in lowered and ("does not exist" in lowered or "not found" in lowered or "unavailable" in lowered):
        return "model_unavailable"
    if status_code in (401, 403):
        if "billing" in lowered or "credit" in lowered or "quota" in lowered:
            return "billing_error"
        return "authentication_error" if status_code == 401 else "authorization_error"
    if status_code == 404:
        return "model_unavailable"
    if status_code == 408:
        return "timeout"
    if status_code == 429:
        if "billing" in lowered or "credit" in lowered:
            return "billing_error"
        return "rate_limit_error" if "rate" in lowered else "quota_error"
    if status_code == 400:
        return "model_unavailable" if "model" in lowered and ("not found" in lowered or "does not exist" in lowered) else "invalid_request"
    if 500 <= status_code < 600:
        return "provider_error"
    return "invalid_request"


def _sanitize_error(category: AIErrorCategory, status_code: int, payload: dict[str, Any] | str, *, provider_code: str | None = None) -> AIExecutionError:
    text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else str(payload)
    if isinstance(payload, dict):
        if "error" in payload and isinstance(payload["error"], dict):
            error = payload["error"]
            text = str(error.get("message") or error.get("type") or text)
            provider_code = provider_code or error.get("code") or error.get("type")
    lowered = text.lower()
    if category == "invalid_request" and ("unsupported_parameter" in lowered or "unsupported_value" in lowered or "max_tokens" in lowered or "temperature" in lowered):
        safe_message = "No se pudo completar la solicitud porque la configuracion de este modelo necesita actualizarse."
    else:
        safe_message = _safe_error_message(text)
    suggested_action = {
        "authentication_error": "Check the stored API key.",
        "authorization_error": "Check provider permissions and account access.",
        "billing_error": "Open provider billing and verify the plan.",
        "rate_limit_error": "Retry later or lower request frequency.",
        "quota_error": "Check provider quota and available credits.",
        "model_unavailable": "Select a different model or verify the catalog.",
        "model_deprecated": "Replace the model assignment.",
        "invalid_request": "Review the request payload and prompt template.",
        "invalid_response": "Repair or reject the provider response.",
        "schema_validation_error": "Adjust the output contract or prompt template.",
        "privacy_block": "Relax the privacy policy or reduce the shared content.",
        "budget_block": "Reduce scope or increase the budget.",
        "timeout": "Retry the request or reduce prompt size.",
        "network_error": "Check network connectivity.",
        "provider_error": "Retry or switch provider with permission.",
        "cancelled_by_user": "No action required.",
        "internal_error": "Inspect local logs and repository state.",
    }.get(category, "Inspect the provider error.")
    if category == "invalid_request" and ("unsupported_parameter" in lowered or "unsupported_value" in lowered or "max_tokens" in lowered or "temperature" in lowered):
        suggested_action = "Actualiza el perfil de solicitud para usar el parametro de salida compatible del modelo."
    retryable = category in {"timeout", "network_error", "rate_limit_error", "provider_error"}
    return AIExecutionError(
        category=category,
        safe_message=safe_message,
        provider_code=str(provider_code or status_code),
        retryable=retryable,
        suggested_action=suggested_action,
        technical_reference=f"HTTP {status_code}" + (f" / {provider_code}" if provider_code else ""),
    )


def _model_display_name(model_id: str, raw: dict[str, Any]) -> str:
    display_name = raw.get("display_name") or raw.get("name")
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    words = [part for part in re.split(r"[-_/\.]+", model_id) if part]
    return " ".join(word.upper() if word.isdigit() else word.replace("gpt", "GPT").replace("claude", "Claude").replace("mini", "mini") for word in words).strip() or model_id


def _supported_model_status(is_compatible: bool) -> str:
    return "testing" if is_compatible else "unavailable"


def _openai_compatibility(model_id: str, raw: dict[str, Any]) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
    lowered = model_id.lower()
    blocked_prefixes = ("text-", "tts-", "whisper", "dall-e", "image-", "moderation", "embedding")
    if lowered.startswith(blocked_prefixes) or "embedding" in lowered or "moderation" in lowered:
        return False, {"endpoint": "chat_completions", "reason": "incompatible_endpoint"}, ("Modelo incompatible con chat/completions.",)
    profile = resolve_provider_request_profile("openai", model_id)
    supports_structured_output = bool(profile.capabilities.supports_structured_output)
    supports_image = bool(profile.capabilities.supports_image_input)
    supports_audio = any(token in lowered for token in ("audio", "realtime", "transcrib", "tts"))
    capabilities = {
        "endpoint": profile.endpoint,
        "structured_output": supports_structured_output,
        "image_input": supports_image,
        "audio_input": supports_audio,
        "source": "provider_discovery",
        "request_profile": profile.to_dict(),
    }
    return True, capabilities, ()


def _anthropic_compatibility(model_id: str, raw: dict[str, Any]) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
    lowered = model_id.lower()
    if not lowered.startswith("claude-"):
        return False, {"endpoint": "messages", "reason": "incompatible_endpoint"}, ("Modelo incompatible con messages.",)
    profile = resolve_provider_request_profile("anthropic", model_id)
    capabilities = {
        "endpoint": profile.endpoint,
        "structured_output": profile.capabilities.supports_structured_output,
        "image_input": profile.capabilities.supports_image_input,
        "audio_input": profile.capabilities.supports_audio_input,
        "source": "provider_discovery",
        "request_profile": profile.to_dict(),
    }
    return True, capabilities, ()


def _normalise_model_rows(provider: AIProviderName, payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        rows = payload.get("data")
        if not isinstance(rows, list):
            rows = payload.get("models")
        if not isinstance(rows, list):
            rows = [payload] if "id" in payload else []
        rows = [item for item in rows if isinstance(item, dict)]
    else:
        rows = []
    seen: set[tuple[str, str | None]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        model_id = str(row.get("id") or row.get("model") or "").strip()
        if not model_id:
            continue
        snapshot = row.get("snapshot") or row.get("version")
        key = (model_id, str(snapshot) if snapshot is not None else None)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _discover_models_from_payload(provider: AIProviderName, payload: dict[str, Any] | list[Any]) -> list[AIProviderDiscoveredModel]:
    raw_rows = _normalise_model_rows(provider, payload)
    models: list[AIProviderDiscoveredModel] = []
    for row in raw_rows:
        model_id = str(row.get("id") or row.get("model") or "").strip()
        if not model_id:
            continue
        if provider == "openai":
            is_compatible, capability_json, notes = _openai_compatibility(model_id, row)
        else:
            is_compatible, capability_json, notes = _anthropic_compatibility(model_id, row)
        display_name = _model_display_name(model_id, row)
        snapshot = row.get("snapshot") or row.get("version") or row.get("revision")
        context_limit = row.get("context_length") or row.get("max_context_length") or row.get("context_window")
        try:
            context_limit = int(context_limit) if context_limit is not None else None
        except (TypeError, ValueError):
            context_limit = None
        models.append(
            AIProviderDiscoveredModel(
                provider=provider,
                model_id=model_id,
                display_name=display_name,
                snapshot_or_version=str(snapshot) if snapshot is not None else None,
                status=_supported_model_status(is_compatible),
                capabilities_json=capability_json,
                context_limit=context_limit,
                supports_structured_output=bool(capability_json.get("structured_output")),
                supports_image_input=bool(capability_json.get("image_input")),
                supports_audio_input=bool(capability_json.get("audio_input")),
                replacement_model_id=row.get("replacement_model_id") or row.get("replacement"),
                compatibility_notes=notes,
            )
        )
    return models


def _sync_report_from_error(provider: AIProviderName, error: AIExecutionError, *, checked_at: str | None = None, latency_ms: int | None = None) -> AIProviderModelSyncReport:
    return AIProviderModelSyncReport(
        provider=provider,
        status="failed",
        message=error.safe_message,
        latency_ms=latency_ms,
        checked_at=checked_at,
        error=error,
        models=(),
    )


@dataclass
class OpenAIProvider:
    provider_name: AIProviderName = "openai"
    base_url: str = "https://api.openai.com/v1"

    def capabilities(self) -> AIProviderCapabilities:
        return AIProviderCapabilities(
            supports_structured_output=True,
            supports_image_input=True,
            supports_audio_input=True,
            supports_retry=True,
            supports_fallback=False,
            modalities=("text", "image", "audio"),
        )

    def test_credentials(self, api_key: str) -> AIProviderDiagnostic:
        started = time.perf_counter()
        try:
            status_code, payload, latency_ms = _http_json(
                "GET",
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                payload=None,
                timeout=20.0,
            )
            if status_code >= 400:
                error = _sanitize_error(_map_error_category(status_code, payload), status_code, payload)
                return AIProviderDiagnostic(
                    provider=self.provider_name,
                    configured=True,
                    model_id=None,
                    status="failed",
                    message=error.safe_message,
                    latency_ms=latency_ms,
                    error=error.to_dict(),
                )
            if not isinstance(payload, dict):
                error = AIExecutionError(
                    category="invalid_response",
                    safe_message="Provider returned a malformed credential response.",
                    retryable=False,
                    suggested_action="Check provider availability.",
                    technical_reference="response",
                )
                return AIProviderDiagnostic(
                    provider=self.provider_name,
                    configured=True,
                    model_id=None,
                    status="failed",
                    message=error.safe_message,
                    latency_ms=latency_ms,
                    error=error.to_dict(),
                )
            return AIProviderDiagnostic(
                provider=self.provider_name,
                configured=True,
                model_id=None,
                status="ok",
                message="OpenAI credentials validated.",
                latency_ms=latency_ms,
                usage={"models": len(payload.get("data", [])) if isinstance(payload, dict) else None},
            )
        except (ConnectionError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="timeout" if isinstance(exc, TimeoutError) else "network_error",
                safe_message=_safe_error_message(str(exc)),
                retryable=True,
                suggested_action="Retry the request or check network connectivity.",
                technical_reference="timeout" if isinstance(exc, TimeoutError) else "network",
            )
            return AIProviderDiagnostic(
                provider=self.provider_name,
                configured=True,
                model_id=None,
                status="failed",
                message=error.safe_message,
                latency_ms=latency_ms,
                error=error.to_dict(),
            )

    def discover_models(self, api_key: str) -> AIProviderModelSyncReport:
        started = time.perf_counter()
        checked_at = None
        try:
            status_code, payload, latency_ms = _http_json(
                "GET",
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                payload=None,
                timeout=20.0,
            )
            checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if status_code >= 400:
                error = _sanitize_error(_map_error_category(status_code, payload), status_code, payload)
                return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)
            if not isinstance(payload, (dict, list)):
                error = AIExecutionError(
                    category="invalid_response",
                    safe_message="Provider returned a malformed model catalog response.",
                    retryable=False,
                    suggested_action="Check provider availability.",
                    technical_reference="response",
                )
                return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)
            models = _discover_models_from_payload(self.provider_name, payload)
            compatible = sum(1 for model in models if model.status in {"approved", "testing"})
            return AIProviderModelSyncReport(
                provider=self.provider_name,
                status="ok",
                message="OpenAI model catalog synchronized.",
                found_count=len(models),
                compatible_count=compatible,
                new_count=0,
                updated_count=0,
                unavailable_count=0,
                latency_ms=latency_ms,
                checked_at=checked_at,
                models=tuple(models),
            )
        except (ConnectionError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="timeout" if isinstance(exc, TimeoutError) else "network_error",
                safe_message=_safe_error_message(str(exc)),
                retryable=True,
                suggested_action="Retry the request or check network connectivity.",
                technical_reference="timeout" if isinstance(exc, TimeoutError) else "network",
            )
            return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)
        except Exception as exc:  # pragma: no cover - defensive normalization
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="invalid_response",
                safe_message=_safe_error_message(str(exc)),
                retryable=False,
                suggested_action="Check provider availability.",
                technical_reference="discovery",
            )
            return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)

    def execute(
        self,
        request: AIExecutionRequest,
        *,
        api_key: str,
        model_id: str,
        prompt_text: str,
    ) -> AIProviderResponse:
        started = time.perf_counter()
        try:
            request_profile = resolve_provider_request_profile("openai", model_id)
            payload = build_openai_diagnostic_payload(
                profile=request_profile,
                model_id=model_id,
                prompt_text=prompt_text,
                max_output_tokens=64,
                include_structured_output=False,
            )
            valid, validation_error = validate_openai_request(payload, request_profile)
            if not valid:
                error = AIExecutionError(
                    category=str(validation_error.get("category") or "invalid_request"),
                    safe_message=str(validation_error.get("safe_message") or "No se pudo completar la solicitud."),
                    provider_code=str(validation_error.get("provider_code") or "invalid_request_error"),
                    retryable=False,
                    suggested_action=str(validation_error.get("suggested_action") or "Review the request payload."),
                    technical_reference=str(validation_error.get("technical_reference") or f"profile={request_profile.profile_id}"),
                )
                return AIProviderResponse(
                    provider=self.provider_name,
                    model_id=model_id,
                    model_version=None,
                    output_text="",
                    structured_output=None,
                    usage=AIExecutionUsage(),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    error=error,
                    warnings=("usage_unavailable",),
                )
            status_code, payload, latency_ms = _http_json(
                "POST",
                f"{self.base_url}/{request_profile.endpoint}",
                headers={"Authorization": f"Bearer {api_key}"},
                payload=payload,
                timeout=30.0,
            )
        except (ConnectionError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="timeout" if isinstance(exc, TimeoutError) else "network_error",
                safe_message=_safe_error_message(str(exc)),
                retryable=True,
                suggested_action="Retry the request or check network connectivity.",
                technical_reference="timeout" if isinstance(exc, TimeoutError) else "network",
            )
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=None,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=latency_ms,
                error=error,
                warnings=("usage_unavailable",),
            )
        if status_code >= 400:
            error = _sanitize_error(_map_error_category(status_code, payload), status_code, payload)
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=None,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=latency_ms,
                error=error,
                warnings=("usage_unavailable",),
            )
        if not isinstance(payload, dict):
            error = AIExecutionError(
                category="invalid_response",
                safe_message="Provider returned malformed JSON.",
                retryable=False,
                suggested_action="Retry the request or fix the model response.",
                technical_reference="response",
            )
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=None,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=latency_ms,
                error=error,
                warnings=("usage_unavailable",),
            )
        parsed = parse_openai_chat_completions_response(payload)
        output_text = parsed["output_text"]
        structured_output = None
        model_version = parsed["model_version"]
        raw_finish_reason = parsed["raw_finish_reason"]
        usage_payload = parsed["usage"]
        usage = AIExecutionUsage(
            input_tokens=int(usage_payload.get("input_tokens") or 0),
            output_tokens=int(usage_payload.get("output_tokens") or 0),
            cached_input_tokens=int(usage_payload.get("cached_input_tokens") or 0),
            reasoning_tokens=usage_payload.get("reasoning_tokens"),
            provider_reported_cost=None,
            calculated_cost=0.0,
            currency="USD",
            pricing_version=None,
            calculation_notes="Provider reported usage normalized locally." if usage_payload.get("has_usage") else "Usage unavailable from provider.",
        )
        usage_missing = not bool(usage_payload.get("has_usage"))
        try:
            structured_output = json.loads(output_text)
        except Exception:
            structured_output = None
        if not output_text:
            error = AIExecutionError(
                category="invalid_response",
                safe_message="Provider response did not include JSON content.",
                retryable=False,
                suggested_action="Retry or adjust the prompt template.",
                technical_reference="response",
            )
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=model_version,
                output_text="",
                structured_output=None,
                usage=usage,
                latency_ms=latency_ms,
                raw_finish_reason=raw_finish_reason,
                error=error,
                warnings=("usage_unavailable",) if usage_missing else (),
            )
        return AIProviderResponse(
            provider=self.provider_name,
            model_id=model_id,
            model_version=model_version,
            output_text=output_text,
            structured_output=structured_output,
            usage=usage,
            latency_ms=latency_ms,
            raw_finish_reason=raw_finish_reason,
            warnings=("usage_unavailable",) if usage_missing else (),
        )


@dataclass
class AnthropicProvider:
    provider_name: AIProviderName = "anthropic"
    base_url: str = "https://api.anthropic.com/v1"
    api_version: str = "2023-06-01"

    def capabilities(self) -> AIProviderCapabilities:
        return AIProviderCapabilities(
            supports_structured_output=True,
            supports_image_input=True,
            supports_audio_input=False,
            supports_retry=True,
            supports_fallback=False,
            modalities=("text", "image"),
        )

    def test_credentials(self, api_key: str) -> AIProviderDiagnostic:
        started = time.perf_counter()
        try:
            status_code, payload, latency_ms = _http_json(
                "GET",
                f"{self.base_url}/models",
                headers={"x-api-key": api_key, "anthropic-version": self.api_version},
                payload=None,
                timeout=20.0,
            )
            if status_code >= 400:
                error = _sanitize_error(_map_error_category(status_code, payload), status_code, payload)
                return AIProviderDiagnostic(
                    provider=self.provider_name,
                    configured=True,
                    model_id=None,
                    status="failed",
                    message=error.safe_message,
                    latency_ms=latency_ms,
                    error=error.to_dict(),
                )
            if not isinstance(payload, dict):
                error = AIExecutionError(
                    category="invalid_response",
                    safe_message="Provider returned a malformed credential response.",
                    retryable=False,
                    suggested_action="Check provider availability.",
                    technical_reference="response",
                )
                return AIProviderDiagnostic(
                    provider=self.provider_name,
                    configured=True,
                    model_id=None,
                    status="failed",
                    message=error.safe_message,
                    latency_ms=latency_ms,
                    error=error.to_dict(),
                )
            return AIProviderDiagnostic(
                provider=self.provider_name,
                configured=True,
                model_id=None,
                status="ok",
                message="Anthropic credentials validated.",
                latency_ms=latency_ms,
                usage={"models": len(payload.get("data", [])) if isinstance(payload, dict) else None},
            )
        except (ConnectionError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="timeout" if isinstance(exc, TimeoutError) else "network_error",
                safe_message=_safe_error_message(str(exc)),
                retryable=True,
                suggested_action="Retry the request or check network connectivity.",
                technical_reference="timeout" if isinstance(exc, TimeoutError) else "network",
            )
            return AIProviderDiagnostic(
                provider=self.provider_name,
                configured=True,
                model_id=None,
                status="failed",
                message=error.safe_message,
                latency_ms=latency_ms,
                error=error.to_dict(),
            )

    def discover_models(self, api_key: str) -> AIProviderModelSyncReport:
        started = time.perf_counter()
        checked_at = None
        try:
            status_code, payload, latency_ms = _http_json(
                "GET",
                f"{self.base_url}/models",
                headers={"x-api-key": api_key, "anthropic-version": self.api_version},
                payload=None,
                timeout=20.0,
            )
            checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if status_code >= 400:
                error = _sanitize_error(_map_error_category(status_code, payload), status_code, payload)
                return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)
            if not isinstance(payload, (dict, list)):
                error = AIExecutionError(
                    category="invalid_response",
                    safe_message="Provider returned a malformed model catalog response.",
                    retryable=False,
                    suggested_action="Check provider availability.",
                    technical_reference="response",
                )
                return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)
            models = _discover_models_from_payload(self.provider_name, payload)
            compatible = sum(1 for model in models if model.status in {"approved", "testing"})
            return AIProviderModelSyncReport(
                provider=self.provider_name,
                status="ok",
                message="Anthropic model catalog synchronized.",
                found_count=len(models),
                compatible_count=compatible,
                new_count=0,
                updated_count=0,
                unavailable_count=0,
                latency_ms=latency_ms,
                checked_at=checked_at,
                models=tuple(models),
            )
        except (ConnectionError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="timeout" if isinstance(exc, TimeoutError) else "network_error",
                safe_message=_safe_error_message(str(exc)),
                retryable=True,
                suggested_action="Retry the request or check network connectivity.",
                technical_reference="timeout" if isinstance(exc, TimeoutError) else "network",
            )
            return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)
        except Exception as exc:  # pragma: no cover - defensive normalization
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="invalid_response",
                safe_message=_safe_error_message(str(exc)),
                retryable=False,
                suggested_action="Check provider availability.",
                technical_reference="discovery",
            )
            return _sync_report_from_error(self.provider_name, error, checked_at=checked_at, latency_ms=latency_ms)

    def execute(
        self,
        request: AIExecutionRequest,
        *,
        api_key: str,
        model_id: str,
        prompt_text: str,
    ) -> AIProviderResponse:
        started = time.perf_counter()
        try:
            request_profile = resolve_provider_request_profile("anthropic", model_id)
            status_code, payload, latency_ms = _http_json(
                "POST",
                f"{self.base_url}/{request_profile.endpoint}",
                headers={"x-api-key": api_key, "anthropic-version": self.api_version},
                payload={
                    "model": model_id,
                    request_profile.output_token_parameter: 128,
                    "temperature": 0,
                    "messages": [
                        {"role": "user", "content": prompt_text},
                    ],
                },
                timeout=30.0,
            )
        except (ConnectionError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            error = AIExecutionError(
                category="timeout" if isinstance(exc, TimeoutError) else "network_error",
                safe_message=_safe_error_message(str(exc)),
                retryable=True,
                suggested_action="Retry the request or check network connectivity.",
                technical_reference="timeout" if isinstance(exc, TimeoutError) else "network",
            )
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=None,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=latency_ms,
                error=error,
                warnings=("usage_unavailable",),
            )
        if status_code >= 400:
            error = _sanitize_error(_map_error_category(status_code, payload), status_code, payload)
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=None,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=latency_ms,
                error=error,
                warnings=("usage_unavailable",),
            )
        if not isinstance(payload, dict):
            error = AIExecutionError(
                category="invalid_response",
                safe_message="Provider returned malformed JSON.",
                retryable=False,
                suggested_action="Retry the request or fix the model response.",
                technical_reference="response",
            )
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=None,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=latency_ms,
                error=error,
                warnings=("usage_unavailable",),
            )
        output_text = ""
        structured_output = None
        usage = AIExecutionUsage()
        model_version = None
        raw_finish_reason = None
        content = payload.get("content") or []
        if content:
            first = content[0] or {}
            output_text = str(first.get("text") or first.get("content") or "")
        model_version = payload.get("model")
        raw_finish_reason = payload.get("stop_reason")
        usage_payload = payload.get("usage") or {}
        usage = AIExecutionUsage(
            input_tokens=int(usage_payload.get("input_tokens") or 0),
            output_tokens=int(usage_payload.get("output_tokens") or 0),
            cached_input_tokens=int(usage_payload.get("cache_read_input_tokens") or 0),
            provider_reported_cost=None,
            calculated_cost=0.0,
            currency="USD",
            pricing_version=None,
            calculation_notes="Provider reported usage normalized locally.",
        )
        try:
            structured_output = json.loads(output_text)
        except Exception:
            structured_output = None
        if not output_text:
            error = AIExecutionError(
                category="invalid_response",
                safe_message="Provider response did not include JSON content.",
                retryable=False,
                suggested_action="Retry or adjust the prompt template.",
                technical_reference="response",
            )
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=model_version,
                output_text="",
                structured_output=None,
                usage=usage,
                latency_ms=latency_ms,
                raw_finish_reason=raw_finish_reason,
                error=error,
            )
        return AIProviderResponse(
            provider=self.provider_name,
            model_id=model_id,
            model_version=model_version,
            output_text=output_text,
            structured_output=structured_output,
            usage=usage,
            latency_ms=latency_ms,
            raw_finish_reason=raw_finish_reason,
        )
