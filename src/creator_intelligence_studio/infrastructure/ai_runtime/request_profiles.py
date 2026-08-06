"""Provider request profiles for AI runtime execution contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


AI_REQUEST_CATALOG_VERSION = "v31-request-profiles-2026-08-06"


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
    profile_id: str
    version: str
    provider: str
    endpoint: str
    model_family: str
    model_family_matcher: str
    model_id: str | None
    output_token_parameter: str
    temperature_policy: str
    top_p_policy: str
    structured_output_policy: str
    reasoning_policy: str
    tools_policy: str
    supported_fields: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    response_parser_profile: str
    usage_parser_profile: str
    status: str
    stability: str
    catalog_version: str
    effective_at: str
    reviewed_at: str
    source_identifier: str
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


def _openai_family(model_id: str) -> tuple[str, str, str, str]:
    lowered = model_id.lower()
    if lowered.startswith("gpt-5.6-"):
        return "gpt-5.6", "^gpt-5\\.6-(sol|terra|luna)(-\\d{4}-\\d{2}-\\d{2})?$", "verified", "https://developers.openai.com/api/docs/models/gpt-5.6-luna"
    if lowered.startswith("gpt-5.1"):
        return "gpt-5.1", "^gpt-5\\.1(-\\d{4}-\\d{2}-\\d{2})?$", "verified", "https://developers.openai.com/api/docs/models/gpt-5.1"
    if lowered.startswith("gpt-5-mini") or lowered == "gpt-5":
        return "gpt-5", "^gpt-5(-mini)?(-\\d{4}-\\d{2}-\\d{2})?$", "verified", "https://developers.openai.com/api/docs/models/gpt-5"
    if lowered.startswith("gpt-4.1"):
        return "gpt-4.1", "^gpt-4\\.1(-\\d{4}-\\d{2}-\\d{2})?$", "verified", "https://developers.openai.com/api/docs/models/gpt-4.1"
    if lowered.startswith("gpt-4o"):
        return "gpt-4o", "^gpt-4o(-mini)?(-\\d{4}-\\d{2}-\\d{2})?$", "verified", "https://developers.openai.com/api/docs/models/gpt-4o-mini"
    return "openai-unknown", "^.*$", "provisional", "https://developers.openai.com/api/docs/models"


def resolve_openai_request_profile(model_id: str) -> OpenAIRequestProfile:
    model_family, matcher, status, source_identifier = _openai_family(model_id)
    lowered = model_id.lower()
    supports_image_input = model_family in {"gpt-5.6", "gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o"}
    supports_structured_output = supports_image_input or lowered.startswith("gpt-5.6-")
    temperature_policy = "omit" if model_family == "gpt-5.6" else "configurable"
    supported_fields = (
        "model",
        "messages",
        "max_completion_tokens",
        "response_format",
    ) if model_family == "gpt-5.6" else (
        "model",
        "messages",
        "max_completion_tokens",
        "temperature",
        "response_format",
    )
    forbidden_fields = (
        "max_tokens",
        "max_output_tokens",
        "top_p",
        "seed",
        "n",
        "stop",
        "stream",
        "tools",
        "tool_choice",
        "parallel_tool_calls",
        "modalities",
        "audio",
        "metadata",
        "user",
        "store",
        "service_tier",
        "logprobs",
        "top_logprobs",
        "presence_penalty",
        "frequency_penalty",
        "reasoning",
        "reasoning_effort",
        "verbosity",
        "input",
        "text.format",
        "json_schema",
    )
    capabilities = OpenAIRequestCapabilities(
        supports_temperature=model_family != "gpt-5.6",
        supports_reasoning_parameters=True,
        supports_structured_output=supports_structured_output,
        supports_image_input=supports_image_input,
        supports_audio_input=False,
        supports_tools=True,
    )
    return OpenAIRequestProfile(
        profile_id=f"openai.{model_family}.chat-completions",
        version=AI_REQUEST_CATALOG_VERSION,
        provider="openai",
        endpoint="chat/completions",
        model_family=model_family,
        model_family_matcher=matcher,
        model_id=model_id,
        output_token_parameter="max_completion_tokens",
        temperature_policy=temperature_policy,
        top_p_policy="omit",
        structured_output_policy="conditional" if supports_structured_output else "unsupported",
        reasoning_policy="unsupported",
        tools_policy="unsupported",
        supported_fields=supported_fields,
        forbidden_fields=forbidden_fields,
        response_parser_profile="chat_completions",
        usage_parser_profile="chat_completions",
        status=status,
        stability="approved" if status == "verified" else "provisional",
        catalog_version=AI_REQUEST_CATALOG_VERSION,
        effective_at="2026-08-06",
        reviewed_at="2026-08-06",
        source_identifier=source_identifier,
        capabilities=capabilities,
        notes=(
            "Chat Completions remains the v31 diagnostic endpoint for OpenAI.",
            "GPT-5.6 Luna omits temperature entirely in the connectivity payload.",
        )
        if model_family == "gpt-5.6"
        else (),
    )


def _anthropic_family(model_id: str) -> tuple[str, str, str]:
    if model_id.lower().startswith("claude-4"):
        return "claude-4", "^claude-4.*$", "verified"
    if model_id.lower().startswith("claude-3.5"):
        return "claude-3.5", "^claude-3\\.5.*$", "verified"
    if model_id.lower().startswith("claude-3"):
        return "claude-3", "^claude-3.*$", "verified"
    return "anthropic-unknown", "^.*$", "provisional"


def resolve_anthropic_request_profile(model_id: str) -> AnthropicRequestProfile:
    model_family, matcher, status = _anthropic_family(model_id)
    capabilities = AnthropicRequestCapabilities(
        supports_temperature=True,
        supports_reasoning_parameters=False,
        supports_structured_output=True,
        supports_image_input=any(token in model_id.lower() for token in ("claude-3", "claude-4", "sonnet", "opus")),
        supports_audio_input=False,
        supports_tools=True,
    )
    return AnthropicRequestProfile(
        profile_id=f"anthropic.{model_family}.messages",
        version=AI_REQUEST_CATALOG_VERSION,
        provider="anthropic",
        endpoint="messages",
        model_family=model_family,
        model_family_matcher=matcher,
        model_id=model_id,
        output_token_parameter="max_tokens",
        temperature_policy="configurable",
        top_p_policy="configurable",
        structured_output_policy="conditional",
        reasoning_policy="unsupported",
        tools_policy="conditional",
        supported_fields=("model", "messages", "max_tokens", "temperature"),
        forbidden_fields=("max_completion_tokens", "max_output_tokens"),
        response_parser_profile="messages",
        usage_parser_profile="messages",
        status=status,
        stability="approved" if status == "verified" else "provisional",
        catalog_version=AI_REQUEST_CATALOG_VERSION,
        effective_at="2026-08-06",
        reviewed_at="2026-08-06",
        source_identifier="https://docs.anthropic.com/",
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
    max_output_tokens: int = 64,
    include_structured_output: bool = False,
    temperature: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Return only the requested JSON object."},
            {"role": "user", "content": prompt_text},
        ],
        profile.output_token_parameter: max_output_tokens,
    }
    if temperature is not None and profile.temperature_policy == "configurable":
        payload["temperature"] = temperature
    if include_structured_output and profile.structured_output_policy == "conditional" and profile.capabilities.supports_structured_output:
        payload["response_format"] = {"type": "json_object"}
    return payload


def validate_openai_request(payload: dict[str, Any], profile: OpenAIRequestProfile) -> tuple[bool, dict[str, Any] | None]:
    allowed_fields = set(profile.supported_fields)
    present_fields = set(payload)
    output_fields = [field for field in ("max_tokens", "max_completion_tokens", "max_output_tokens") if field in payload]
    if payload.get("model") != profile.model_id:
        return False, {
            "category": "invalid_request",
            "provider_code": "invalid_request_error",
            "safe_message": "No se pudo completar la solicitud porque el modelo no coincide con el perfil validado.",
            "suggested_action": "Revisar el perfil de solicitud antes de volver a intentar.",
            "technical_reference": f"profile={profile.profile_id}",
        }
    if len(output_fields) != 1 or output_fields[0] != profile.output_token_parameter:
        return False, {
            "category": "invalid_request",
            "provider_code": "unsupported_parameter",
            "safe_message": "No se pudo completar la solicitud porque el parametro de salida no coincide con el perfil validado.",
            "suggested_action": "Usar el parametro de salida compatible del perfil.",
            "technical_reference": f"profile={profile.profile_id}",
        }
    if profile.temperature_policy == "omit" and "temperature" in payload:
        return False, {
            "category": "invalid_request",
            "provider_code": "unsupported_value",
            "safe_message": "No se pudo completar la solicitud porque la configuracion de este modelo necesita actualizarse.",
            "suggested_action": "Omitir temperature para este modelo.",
            "technical_reference": f"profile={profile.profile_id} field=temperature",
        }
    unexpected = [field for field in present_fields if field not in allowed_fields]
    if unexpected:
        return False, {
            "category": "invalid_request",
            "provider_code": "unsupported_parameter",
            "safe_message": "No se pudo completar la solicitud porque contiene campos no soportados por este perfil.",
            "suggested_action": "Eliminar los campos no soportados y reintentar.",
            "technical_reference": f"profile={profile.profile_id} fields={','.join(sorted(unexpected))}",
        }
    if not isinstance(payload.get("messages"), list) or not payload["messages"]:
        return False, {
            "category": "invalid_request",
            "provider_code": "invalid_request_error",
            "safe_message": "No se pudo completar la solicitud porque el formato de mensajes no es valido.",
            "suggested_action": "Corregir el formato de mensajes antes de volver a intentar.",
            "technical_reference": f"profile={profile.profile_id}",
        }
    return True, None


def describe_openai_request_payload(*, endpoint: str, profile: OpenAIRequestProfile, payload: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, str] = {}
    for key, value in payload.items():
        if key == "messages" and isinstance(value, list):
            fields[key] = "redacted:list"
        elif key == "response_format" and isinstance(value, dict):
            fields[key] = "object"
        elif isinstance(value, bool):
            fields[key] = "bool"
        elif isinstance(value, int):
            fields[key] = "integer"
        elif isinstance(value, float):
            fields[key] = "number"
        elif isinstance(value, str):
            fields[key] = "string"
        elif isinstance(value, list):
            fields[key] = "list"
        elif isinstance(value, dict):
            fields[key] = "object"
        elif value is None:
            fields[key] = "null"
        else:
            fields[key] = type(value).__name__
    return {
        "endpoint": endpoint,
        "method": "POST",
        "model": profile.model_id,
        "profile": profile.profile_id,
        "profile_version": profile.version,
        "status": profile.status,
        "fields": fields,
    }


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


def _normalize_chat_completion_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        candidate = value.get("value")
        if candidate is None:
            candidate = value.get("text")
        if candidate is None:
            candidate = value.get("content")
        return _normalize_chat_completion_text(candidate)
    if isinstance(value, list):
        fragments: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").lower()
            if item_type not in {"text", "output_text"}:
                continue
            text_value = item.get("text")
            if isinstance(text_value, dict):
                fragment = text_value.get("value")
                if fragment is None:
                    fragment = text_value.get("text")
            else:
                fragment = text_value
            if fragment is None:
                fragment = item.get("value")
            if fragment is None:
                fragment = item.get("content")
            if fragment is None:
                continue
            fragments.append(str(fragment))
        return "\n".join(fragment.strip() for fragment in fragments if str(fragment).strip()).strip()
    return str(value).strip()


def _openai_chat_completion_response_state(*, content_text: str, refusal_text: str | None, finish_reason: str | None) -> str:
    reason = (finish_reason or "").strip().lower()
    if refusal_text:
        return "refusal"
    if reason == "content_filter":
        return "content_filter"
    if reason == "length":
        return "truncated"
    if content_text:
        return "content"
    return "empty"


def parse_openai_chat_completions_response(payload: dict[str, Any]) -> dict[str, Any]:
    output_text = ""
    raw_finish_reason = None
    refusal_text = None
    content_shape = "missing"
    message_shape = "missing"
    choices = payload.get("choices") or []
    if choices:
        choice = choices[0] or {}
        message = choice.get("message") or {}
        message_shape = type(message).__name__
        raw_content = message.get("content")
        if isinstance(raw_content, str):
            content_shape = "string"
        elif isinstance(raw_content, list):
            content_shape = "array"
        elif raw_content is None:
            content_shape = "missing"
        else:
            content_shape = type(raw_content).__name__
        output_text = _normalize_chat_completion_text(raw_content)
        refusal_value = message.get("refusal")
        if refusal_value is None and isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, dict) and str(item.get("type") or "").lower() == "refusal":
                    refusal_value = item.get("refusal") or item.get("text") or item.get("content")
                    if refusal_value is not None:
                        break
        refusal_text = _normalize_chat_completion_text(refusal_value) or None
        raw_finish_reason = choice.get("finish_reason")
    usage = extract_openai_usage(payload)
    response_state = _openai_chat_completion_response_state(
        content_text=output_text,
        refusal_text=refusal_text,
        finish_reason=raw_finish_reason,
    )
    return {
        "output_text": output_text,
        "content_text": output_text,
        "content_shape": content_shape,
        "message_shape": message_shape,
        "content_length": len(output_text),
        "refusal_text": refusal_text,
        "structured_output": None,
        "model_version": payload.get("model"),
        "raw_finish_reason": raw_finish_reason,
        "response_state": response_state,
        "parser_profile": "chat_completions",
        "usage": usage,
    }
