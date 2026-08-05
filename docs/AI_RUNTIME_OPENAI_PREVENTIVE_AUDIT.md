# AI Runtime OpenAI Preventive Audit

## Scope

Audit of the real v31 diagnostic path:

`GUI -> service -> orchestrator -> policy -> OpenAI adapter -> HTTP -> response -> normalization -> validation -> persistence -> history`

Authority is limited to official OpenAI documentation and the repository implementation/tests in this workspace.

## Source Register

| Rule / capability | Source | reviewed_at | effective_at | confidence | catalog_version |
|---|---|---|---|---|---|
| gpt-5.6-luna model guidance, supported endpoints, pricing | https://developers.openai.com/api/docs/models/gpt-5.6-luna | 2026-08-05 | 2026-08-05 | high | v31-request-profiles-2026-08-05 |
| OpenAI GPT-5.6 model guidance | https://platform.openai.com/docs/models/gpt-5-6 | 2026-08-05 | 2026-08-05 | high | v31-request-profiles-2026-08-05 |
| OpenAI model compare page | https://platform.openai.com/docs/models/compare | 2026-08-05 | 2026-08-05 | high | v31-request-profiles-2026-08-05 |
| Chat Completions request reference | https://platform.openai.com/docs/api-reference/chat/create | 2026-08-05 | 2026-08-05 | high | v31-request-profiles-2026-08-05 |
| Responses API request reference | https://platform.openai.com/docs/api-reference/responses/create | 2026-08-05 | 2026-08-05 | high | v31-request-profiles-2026-08-05 |
| Structured Outputs guide | https://platform.openai.com/docs/guides/structured-outputs | 2026-08-05 | 2026-08-05 | high | v31-request-profiles-2026-08-05 |

## Findings Table

| Hallazgo | Evidencia | Severidad | Estado | Accion |
|---|---|---:|---|---|
| gpt-5.6-luna recibia max_tokens en el request real | HTTP 400 real del proveedor; reproduced in provider tests; fixed in the adapter payload builder | alta | corrected_now | Use max_completion_tokens on Chat Completions and omit max_tokens. |
| Endpoint actual sigue siendo Chat Completions | OpenAI guidance and compare page list v1/chat/completions for gpt-5.6-luna | media | already_covered | Keep the current endpoint for v31. |
| Request profile resolution was dispersed | New centralized ProviderRequestProfile and OpenAI/Anthropic profile classes | media | corrected_now | Route endpoint and output parameter decisions through the profile layer. |
| Structured output contract is profile driven | Diagnostic payload builder only adds response_format when the profile supports it | media | already_covered | Keep the schema path minimal and provider aware. |
| Usage may be absent on error or invalid responses | Provider parser now marks usage as unavailable instead of forcing zeros | media | corrected_now | Preserve None semantics in cost and usage reporting. |
| Error normalization previously exposed a generic failure for unsupported parameters | Adapter now maps unsupported_parameter / max_tokens to a user friendly Spanish message | media | corrected_now | Keep the primary GUI message generic and safe. |
| Retry policy should not retry 400-class compatibility errors | Retryable set excludes 400/401/403/404/schema errors | low | already_covered | Do not expand retries for invalid contracts. |
| Cache must not alias incompatible request profiles | Cache fingerprint includes provider, model, endpoint, template, schema, context, and privacy dimensions | media | already_covered | Preserve profile aware fingerprints. |
| Catalog synchronization can become stale when models retire | Current code detects model resolution failures at resume time | media | risk_needs_real_test | Keep regression coverage for model removal between sync and execution. |
| GUI feedback should be user friendly for incompatible parameters | Overview view now emits a Spanish guidance message for compatibility mismatches | low | corrected_now | Keep raw provider details out of the main message. |
| Fakes can create false confidence if they accept any payload | Provider tests now assert request fields for the OpenAI path | media | corrected_now | Keep the fake strict on output-token parameter and endpoint shape. |
| Anthropic boundary must remain separate | Request profile abstraction is provider neutral and keeps Anthropic on its own contract | low | already_covered | Do not route product logic directly to provider-specific SDK assumptions. |

## Parameter Audit

| Parameter | Current status in v31 diagnostic path | Classification |
|---|---|---|
| max_tokens | Not sent to OpenAI diagnostic requests after the fix | incompatible confirmed for gpt-5.6-luna on current endpoint |
| max_completion_tokens | Sent for OpenAI Chat Completions diagnostics | compatible confirmed |
| max_output_tokens | Not used in the current Chat Completions path | no utilizado en diagnostico |
| temperature | Sent as 0 when the profile allows it | compatible confirmed |
| top_p | Not sent | debe omitirse |
| seed | Not sent | debe omitirse |
| response_format | Sent only when structured output is enabled by the profile | compatible confirmado |
| structured output schema | Minimal JSON object diagnostic contract | compatible confirmed |
| reasoning effort | Not sent in the current v31 diagnostic path | no utilizado en diagnostico |
| verbosity | Not sent | debe omitirse |
| tools | Not sent | debe omitirse |
| tool_choice | Not sent | debe omitirse |
| modalities | Not sent | debe omitirse |
| audio | Not sent | debe omitirse |
| image input | Not used by the diagnostic payload | no utilizado en diagnostico |
| stream | Not sent | debe omitirse |
| stop | Not sent | debe omitirse |
| n | Not sent | debe omitirse |
| logprobs | Not sent | debe omitirse |
| timeout | Request timeout is set in the HTTP adapter layer | compatible confirmado |
| metadata | Not sent to the OpenAI diagnostic payload | debe omitirse |

## Contract Notes

### Endpoint

- Current endpoint: chat/completions
- The v31 fix keeps the existing endpoint and makes the output-token parameter compatible with gpt-5.6-luna.

### Payload

Safe diagnostic payload fields:

`model`, `messages`, `max_completion_tokens`, `temperature`, `response_format`

`max_tokens` is not present in the corrected OpenAI request.

### Response Parsing

- Chat Completions parsing uses `choices[0].message.content` as the text source.
- Usage parsing prefers OpenAI-style `prompt_tokens` / `completion_tokens` and falls back to compatible aliases when present.
- When usage is missing, the runtime now marks it as unavailable instead of pretending it was measured.

### Error Normalization

Validated categories in the OpenAI adapter path:

- unsupported_parameter -> user friendly compatibility message
- invalid_request_error -> request payload problem
- authentication_error
- authorization_error
- quota_error
- rate_limit_error
- provider_error
- timeout
- network_error

### Cache And Approval

- Cache hits are keyed by provider, model, endpoint, template, schema, context, privacy, and request semantics.
- Approval reuse remains on the same execution row and same execution_uuid for the resumed path.
- A failed unsupported_parameter execution can be retried through a fresh bypass path after the fix.

## Risks Still Pending

| Hallazgo | Evidencia | Severidad | Estado | Accion |
|---|---|---:|---|---|
| Full discover run exceeds the shorter tool timeout in this workspace | python -m unittest discover -s tests -p "test_ai_runtime_*.py" timed out under the shorter window | media | risk_needs_real_test | Run the larger suite with a longer budget or split by file when validating locally. |
| GUI suite is slow because it recreates the full runtime fixture repeatedly | python -m unittest tests.test_ai_runtime_gui timed out under the shorter window | media | risk_needs_real_test | Keep the file-level test in CI with a longer timeout. |

## Out Of Scope

- no provider migration to Responses API in v31
- no Anthropic changes
- no Component Manager work
- no automatic video editing
- no new provider integrations
- no schema overhaul
