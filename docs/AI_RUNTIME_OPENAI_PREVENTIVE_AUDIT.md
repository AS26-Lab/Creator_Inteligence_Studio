# AI Runtime OpenAI Preventive Audit

## Scope

Audit of the real v31 diagnostic path:

`GUI -> service -> orchestrator -> policy -> OpenAI adapter -> HTTP -> response -> normalization -> validation -> persistence -> history`

Authority is limited to official OpenAI documentation and the repository implementation/tests in this workspace.

## Source Register

| Rule / capability | Source identifier or URL | reviewed_at | effective_at | confidence | catalog_version |
|---|---|---|---|---|---|
| GPT-5.6 Luna model page, endpoints, modalities, pricing, structured outputs, snapshots | https://developers.openai.com/api/docs/models/gpt-5.6-luna | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |
| GPT-5.6 model guidance and parameter recommendations | https://developers.openai.com/api/docs/guides/latest-model | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |
| Model compare page for GPT-5.6 family endpoint confirmation | https://developers.openai.com/api/docs/models/compare | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |
| OpenAI model object reference for catalog discovery | https://platform.openai.com/docs/api-reference/models/object?lang=curl | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |
| Chat Completions request contract (legacy families) | https://platform.openai.com/docs/api-reference/chat/create | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |
| Responses API request contract | https://platform.openai.com/docs/api-reference/responses/create | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |
| Structured Outputs guide | https://platform.openai.com/docs/guides/structured-outputs | 2026-08-06 | 2026-08-06 | high | v31-request-profiles-2026-08-06 |

## Findings Table

| Hallazgo | Evidencia | Severidad | Estado | Acción |
|---|---|---:|---|---|
| gpt-5.6-luna sent max_tokens in an earlier request path | Reproduced provider 400; corrected by switching the output token parameter to `max_completion_tokens` | alta | corrected_now | Keep `max_tokens` out of OpenAI Chat Completions for GPT-5.6. |
| gpt-5.6-luna also sent temperature=0 in the previous payload | Reproduced by strict contract validation; corrected by omitting temperature in the minimal GPT-5.6 payload | alta | corrected_now | Omit temperature for GPT-5.6 Luna diagnostics. |
| GPT-5.6 Luna diagnostic now uses Responses API | GPT-5.6 Luna model page and model guidance recommend Responses API for reasoning workflows; local contract tests now validate `v1/responses` with `reasoning.effort=none` | alta | corrected_now | Keep GPT-5.6 diagnostics on Responses API and leave Chat Completions for legacy families only. |
| Request profiles are now centralized and versioned | New `ProviderRequestProfile` / `OpenAIRequestProfile` contract and validator | media | corrected_now | Route endpoint and output-token decisions through the profile layer. |
| Minimal payload is now enforced before HTTP | `build_openai_diagnostic_payload` omits optional fields by default; `validate_openai_request` blocks unsupported fields locally | media | corrected_now | Validate the serialized payload before calling the provider. |
| Structured output is conditional, not unconditional | `response_format` is only added when explicitly requested and profile-supported | media | already_covered | Keep connectivity diagnostics minimal unless structured output is required. |
| Response parsing now distinguishes textual connectivity from structured validation | New parser metadata tracks `content_shape`, `response_state`, and `finish_reason`; the orchestrator no longer coerces text responses into JSON-only validation | media | corrected_now | Validate structured output separately from plain text connectivity. |
| Usage can be absent or partial | Parser now preserves absence as unavailable rather than fabricating measured zeros | media | corrected_now | Keep `None`/unavailable semantics in cost and usage tracking. |
| Error normalization must distinguish compatibility errors | Adapter and fake now surface unsupported_value / unsupported_parameter safely | media | corrected_now | Translate contract errors to a user-friendly Spanish message. |
| Preview/snapshot models should not auto-promote to verified recommendations | `classify_model_for_role()` now short-circuits preview/snapshot variants before capability fallback | media | corrected_now | Keep previews in compatibility_unknown unless a verified rule exists. |
| Retry policy should not retry 400-class compatibility errors | Retryable set excludes 400/401/403/404/schema errors | low | already_covered | Keep retries conservative. |
| Cache must not alias incompatible request profiles | Cache and execution fingerprints preserve provider/model/endpoint/template/context semantics | media | already_covered | Keep profile-aware fingerprints. |
| Strict fake prevents false confidence | `StrictOpenAIContractFake` rejects incompatible payloads and validates the final serialized request | media | corrected_now | Keep the fake strict by default in contract tests. |
| Anthropic boundary remains separate | Request profile abstraction is provider-neutral and Anthropic stays on its own contract | low | already_covered | Do not couple the new OpenAI contract to Anthropic behavior. |

## Field Audit

| Campo | Quién lo agrega | Valor/default | Endpoint | Perfil/familia | Compatibilidad | Acción |
|---|---|---|---|---|---|---|
| model | request builder | model_id exacto | responses | gpt-5.6 family | confirmed_supported | include |
| input | request builder | prompt corto y textual | responses | gpt-5.6 family | confirmed_supported | include |
| max_tokens | legacy compatibility path | no se envía | responses | gpt-5.6 family | confirmed_unsupported | omit |
| max_completion_tokens | chat compatibility only | no se envía | responses | gpt-5.6 family | confirmed_unsupported | omit |
| max_output_tokens | request builder | 256 en diagnósticos de conectividad | responses | gpt-5.6 family | confirmed_supported | include |
| reasoning | request builder | `{"effort":"none"}` | responses | gpt-5.6 family | confirmed_supported | include |
| temperature | request profile only when configurable | omit en gpt-5.6 | responses | gpt-5.6 family | confirmed_unsupported | omit |
| top_p | no usado en diagnóstico | omitido | responses | gpt-5.6 family | not_used | omit |
| seed | no usado en diagnóstico | omitido | responses | gpt-5.6 family | not_used | omit |
| response_format | structured diagnostic only | omitido por defecto | responses | gpt-5.6 family | not_used | omit |
| text.format | structured-output capability only | omitido | responses | gpt-5.6 family | not_used | omit |
| json_schema | structured-output capability only | omitido | responses | gpt-5.6 family | not_used | omit |
| reasoning / reasoning_effort | no usado por el diagnóstico básico | reasoning.effort only | responses | gpt-5.6 family | confirmed_supported | omit |
| verbosity | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| tools | no usado | omitido | responses | gpt-5.6 family | confirmed_supported at model level | omit |
| tool_choice | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| modalities | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| audio | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| image input | capability only | not part of the minimal payload | responses | gpt-5.6 family | confirmed_supported at model level | report_only |
| stream | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| stop | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| n | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| logprobs | no usado | omitido | responses | gpt-5.6 family | not_used | omit |
| timeout | HTTP adapter layer | 30s execute / 20s credential and model sync | provider adapter | both providers | confirmed_supported | validate |
| metadata | no usado | omitido | responses | gpt-5.6 family | not_used | omit |

## Contract Notes

### Endpoint

- Current endpoint for GPT-5.6 Luna connectivity diagnostics: `responses`.
- Chat Completions remains available for legacy OpenAI families that still use it.

### Payload

Safe diagnostic payload fields after serialization:

`model`, `input`, `max_output_tokens`, `reasoning`

`temperature`, `top_p`, `tools`, `response_format`, and structured-output schema fields are omitted from the minimal connectivity diagnostic.
`reasoning.effort` is set to `none` for GPT-5.6 Luna connectivity.

### Response Parsing

- Responses API parsing uses `status`, `output`, `output_text`, and `incomplete_details.reason` as the primary response signals.
- Chat Completions parsing remains in place for legacy models and still accepts string content, content arrays, refusal states, and empty/truncated shapes without conflating them with HTTP transport failures.
- Usage parsing prefers `input_tokens` / `output_tokens` and compatible aliases when present, while preserving `reasoning_tokens` when the provider reports them.
- When usage is missing, the runtime records unavailable usage instead of fabricating zeros.
- The orchestrator passes textual connectivity responses through a textual validator path instead of forcing an empty dict into structured-output validation.

### Error Normalization

Validated categories in the OpenAI adapter path:

- `unsupported_parameter` -> user-friendly compatibility message
- `unsupported_value` -> user-friendly compatibility message
- `invalid_request_error` -> request payload problem
- `authentication_error`
- `authorization_error`
- `quota_error`
- `rate_limit_error`
- `provider_error`
- `timeout`
- `network_error`

### Cache And Approval

- Cache hits are keyed by provider, model, endpoint, template, schema, context, privacy, and request semantics.
- Approval reuse remains on the same execution row and same `execution_uuid` for the resumed path.
- A failed unsupported_parameter or unsupported_value execution can be retried through a fresh bypass path after the fix.

## Tests Executed

Passed:

- `python -m unittest tests.test_openai_response_contracts`
- `python -m unittest tests.test_openai_diagnostic_validation`
- `python -m unittest tests.test_openai_request_contracts`
- `python -m unittest tests.test_openai_error_contracts`
- `python -m unittest tests.test_openai_diagnostic_e2e`
- `python -m unittest tests.test_ai_runtime_recommended_model_contracts`
- `python -m unittest tests.test_ai_runtime_request_profiles`
- `python -m unittest tests.test_ai_runtime_providers`
- `python -m unittest tests.test_ai_runtime_foundation`
- targeted GUI cases around diagnostics, approvals, provider errors, and double-click blocking
- `python -m creator_intelligence_studio --diagnostic-json`

Timed out in this workspace window:

- `python -m unittest tests.test_ai_runtime_orchestrator`
- `python -m unittest tests.test_ai_runtime_gui`
- `python -m unittest discover -s tests -p "test_ai_runtime_*.py"`
- the full orchestrator module also timed out on a longer 360s retry in this workspace

## Risks Still Pending

| Hallazgo | Evidencia | Severidad | Estado | Acción |
|---|---|---:|---|---|
| Full discover run exceeds the shorter tool timeout in this workspace | `python -m unittest discover -s tests -p "test_ai_runtime_*.py"` timed out under the 120s window | media | risk_needs_real_test | Run the larger suite with a longer budget or split by file in CI. |
| GUI and orchestrator files still need longer wall-clock time in this workspace | `python -m unittest tests.test_ai_runtime_orchestrator` and `python -m unittest tests.test_ai_runtime_gui` timed out under the 120s window | media | risk_needs_real_test | Keep those suites in CI with a longer budget. |
| Structured-output certification remains separate from the connectivity diagnostic | The basic diagnostic now uses Responses API text-only mode and intentionally omits structured output; capability certification is opt-in and tested separately | media | future_improvement | Keep the connectivity diagnostic minimal and run structured-output certification as a separate gate. |

## Out Of Scope

- no provider migration to Responses API in v31
- no Anthropic changes
- no Component Manager work
- no automatic video editing
- no new provider integrations
- no schema overhaul
