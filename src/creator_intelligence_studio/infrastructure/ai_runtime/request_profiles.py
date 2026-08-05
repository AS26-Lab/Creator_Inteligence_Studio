"""Provider request profiles for AI runtime execution contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


AI_REQUEST_CATALOG_VERSION = "v31-request-profiles-2026-08-05"


@dataclass(frozen=True, slots=True)
class ProviderRequestCapabilities:
    supports_temperature: bool
    supports_reasoning_parameters: bool
    supports_structured_output: bool
    supports_image_input: bool
    supports_audio_input: bool
    supports_tools: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProviderRequestProfile:
    provider: str
    endpoint: str
    output_token_parameter: str
    response_parser_profile: str
    usage_parser_profile: str
    stability: str
    catalog_version: str
    effective_at: str
    reviewed_at: str
    source_identifier: str
    model_family: str
    model_id: str | None
    capabilities: ProviderRequestCapabilities
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = self.capabilities.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class OpenAIRequestCapabilities(ProviderRequestCapabilities):
    pass


@dataclass(frozen=True, slots=True)
class OpenAIRequestProfile(ProviderRequestProfile):
    capabilities: OpenAIRequestCapabilities


@dataclass(frozen=True, slots=True)
class AnthropicRequestCapabilities(ProviderRequestCapabilities):
    pass


@dataclass(frozen=True, slots=True)
class AnthropicRequestProfile(ProviderRequestProfile):
    capabilities: AnthropicRequestCapabilities


def _openai_family(model_id: str) -> tuple[str, str, str]:
    lowered = model_id.lower()
    if lowered.startswith("gpt-5.6-"):
        return "gpt-5.6", "https://developers.openai.com/api/docs/models/gpt-5.6-luna", "approved"
    if lowered.startswith("gpt-5.1"):
        return "gpt-5.1", "https://developers.openai.com/api/docs/models/gpt-5.1", "approved"
    if lowered.startswith("gpt-5-mini") or lowered == "gpt-5":
        return "gpt-5", "https://developers.openai.com/api/docs/models/gpt-5", "approved"
    if lowered.startswith("gpt-4.1"):
        return "gpt-4.1", "https://developers.openai.com/api/docs/models/gpt-4.1", "approved"
    if lowered.startswith("gpt-4o"):
        return "gpt-4o", "https://developers.openai.com/api/docs/models/gpt-4o-mini", "approved"
    return "openai-unknown", "https://developers.openai.com/api/docs/models", "provisional"


def resolve_openai_request_profile(model_id: str) -> OpenAIRequestProfile:
    model_family, source_identifier, stability = _openai_family(model_id)
    lowered = model_id.lower()
    supports_image_input = model_family in {"gpt-5.6", "gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o"}
    supports_structured_output = supports_image_input or lowered.startswith("gpt-5.6-")
    capabilities = OpenAIRequestCapabilities(
        supports_temperature=True,
        supports_reasoning_parameters=True,
        supports_structured_output=supports_structured_output,
        supports_image_input=supports_image_input,
        supports_audio_input=False,
        supports_tools=True,
    )
    return OpenAIRequestProfile(
        provider="openai",
        endpoint="chat/completions",
        output_token_parameter="max_completion_tokens",
        response_parser_profile="chat_completions",
        usage_parser_profile="chat_completions",
        stability=stability,
        catalog_version=AI_REQUEST_CATALOG_VERSION,
        effective_at="2026-08-05",
        reviewed_at="2026-08-05",
        source_identifier=source_identifier,
        model_family=model_family,
        model_id=model_id,
        capabilities=capabilities,
        notes=(
            "Use the Chat Completions endpoint until a deliberate Responses API migration is approved.",
            "GPT-5.6 Luna uses max_completion_tokens on Chat Completions.",
        )
        if model_family == "gpt-5.6"
        else (),
    )


def _anthropic_family(model_id: str) -> tuple[str, str]:
    if model_id.lower().startswith("claude-4"):
        return "claude-4", "https://docs.anthropic.com/"
    if model_id.lower().startswith("claude-3.5"):
        return "claude-3.5", "https://docs.anthropic.com/"
    if model_id.lower().startswith("claude-3"):
        return "claude-3", "https://docs.anthropic.com/"
    return "anthropic-unknown", "https://docs.anthropic.com/"


def resolve_anthropic_request_profile(model_id: str) -> AnthropicRequestProfile:
    model_family, source_identifier = _anthropic_family(model_id)
    lowered = model_id.lower()
    capabilities = AnthropicRequestCapabilities(
        supports_temperature=True,
        supports_reasoning_parameters=False,
        supports_structured_output=True,
        supports_image_input=any(token in lowered for token in ("claude-3", "claude-4", "sonnet", "opus")),
        supports_audio_input=False,
        supports_tools=True,
    )
    return AnthropicRequestProfile(
        provider="anthropic",
        endpoint="messages",
        output_token_parameter="max_tokens",
        response_parser_profile="messages",
        usage_parser_profile="messages",
        stability="approved" if model_family != "anthropic-unknown" else "provisional",
        catalog_version=AI_REQUEST_CATALOG_VERSION,
        effective_at="2026-08-05",
        reviewed_at="2026-08-05",
        source_identifier=source_identifier,
        model_family=model_family,
        model_id=model_id,
        capabilities=capabilities,
    )


def resolve_provider_request_profile(provider: str, model_id: str) -> ProviderRequestProfile:
    provider_lower = provider.lower()
    if provider_lower == "openai":
        return resolve_openai_request_profile(model_id)
    if provider_lower == "anthropic":
        return resolve_anthropic_request_profile(model_id)
    raise ValueError(f"Unsupported provider '{provider}'.")


def build_openai_diagnostic_payload(
    *,
    profile: OpenAIRequestProfile,
    model_id: str,
    prompt_text: str,
    max_output_tokens: int = 128,
    include_response_format: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Return only the requested JSON object."},
            {"role": "user", "content": prompt_text},
        ],
        profile.output_token_parameter: max_output_tokens,
    }
    if profile.capabilities.supports_temperature:
        payload["temperature"] = 0
    if include_response_format and profile.capabilities.supports_structured_output:
        payload["response_format"] = {"type": "json_object"}
    return payload


def extract_openai_usage(payload: dict[str, Any]) -> dict[str, Any]:
    usage_payload = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    input_tokens = usage_payload.get("prompt_tokens")
    if input_tokens is None:
        input_tokens = usage_payload.get("input_tokens")
    output_tokens = usage_payload.get("completion_tokens")
    if output_tokens is None:
        output_tokens = usage_payload.get("output_tokens")
    cached_input_tokens = usage_payload.get("cached_tokens")
    prompt_details = usage_payload.get("prompt_tokens_details") if isinstance(usage_payload.get("prompt_tokens_details"), dict) else {}
    if cached_input_tokens is None and isinstance(prompt_details, dict):
        cached_input_tokens = prompt_details.get("cached_tokens")
    if cached_input_tokens is None:
        input_details = usage_payload.get("input_tokens_details") if isinstance(usage_payload.get("input_tokens_details"), dict) else {}
        if isinstance(input_details, dict):
            cached_input_tokens = input_details.get("cached_tokens")
    reasoning_tokens = usage_payload.get("reasoning_tokens")
    if reasoning_tokens is None:
        output_details = usage_payload.get("completion_tokens_details") if isinstance(usage_payload.get("completion_tokens_details"), dict) else {}
        if isinstance(output_details, dict):
            reasoning_tokens = output_details.get("reasoning_tokens")
    if reasoning_tokens is None and isinstance(usage_payload.get("output_tokens_details"), dict):
        reasoning_tokens = usage_payload["output_tokens_details"].get("reasoning_tokens")
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "cached_input_tokens": int(cached_input_tokens or 0),
        "reasoning_tokens": int(reasoning_tokens) if reasoning_tokens is not None else None,
        "has_usage": bool(usage_payload),
    }


def parse_openai_chat_completions_response(payload: dict[str, Any]) -> dict[str, Any]:
    output_text = ""
    raw_finish_reason = None
    choices = payload.get("choices") or []
    if choices:
        choice = choices[0] or {}
        message = choice.get("message") or {}
        output_text = str(message.get("content") or "")
        raw_finish_reason = choice.get("finish_reason")
    usage = extract_openai_usage(payload)
    return {
        "output_text": output_text,
        "structured_output": None,
        "model_version": payload.get("model"),
        "raw_finish_reason": raw_finish_reason,
        "usage": usage,
    }

