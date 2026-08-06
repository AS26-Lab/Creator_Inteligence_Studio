# AI Runtime and Provider Orchestration Foundation

## Status

Implemented as v31 foundation. This document defines the canonical contract for the first AI execution layer in Creator Intelligence Studio.

The foundation is intentionally narrow:

- it enables provider diagnostics and the surrounding orchestration contract;
- it does not implement creative script generation, corpus learning, embeddings, semantic retrieval, or AI-assisted video editing;
- it keeps modules from calling OpenAI or Anthropic directly;
- it preserves human control, privacy, cost control, and reproducibility.

## Scope

Included:

- provider credential storage;
- provider diagnostics;
- provider model catalog discovery and synchronization;
- role-based model resolution;
- prompt template registry;
- budget policy checks;
- privacy policy checks;
- cost estimation and usage tracking;
- execution persistence;
- cache entries for exact diagnostic reuse;
- CLI access;
- GUI visibility for status, roles, budgets, diagnostics, and history;
- Task Center visibility for diagnostic tasks.

Paused:

- guiones reales;
- hooks reales;
- titles, captions, recommendations, and packaging generation through AI;
- multimodal understanding beyond this diagnostic foundation;
- corpus, embeddings, retrieval, feedback learning;
- vision and audio AI product flows;
- publication automation;
- video editing automation.

## Architecture

The execution path is:

`product module -> AIExecutionRequest -> AIOrchestrator -> privacy -> budget -> role resolution -> provider -> validation -> persistence -> AIExecutionResult`

Direct provider calls are not allowed from product modules.

### Core Interfaces

- `AIProvider`
- `OpenAIProvider`
- `AnthropicProvider`
- `AIOrchestrator`
- `ProviderRequestProfile`
- `OpenAIRequestProfile`
- `OpenAIRequestCapabilities`
- `AnthropicRequestProfile`
- `AnthropicRequestCapabilities`
- `ModelRegistry`
- `PromptRegistry`
- `CredentialStore`
- `CostEstimator`
- `CostTracker`
- `BudgetPolicy`
- `PrivacyPolicyEngine`
- `AIExecutionRepository`
- `AIResultValidator`
- `AICache`

### Supported Providers

Only these providers are enabled for stage one:

1. OpenAI
2. Anthropic

No third provider is normalized in this phase.

### Replaceable Roles

The system uses conceptual roles instead of hard-coded model names:

- `cheap_structured_model`
- `general_reasoning_model`
- `creative_writing_model`
- `multimodal_model`
- `transcription_fallback_model`
- `evaluation_model`

Role assignments are stored in the catalog and can be overridden per creator.

## Migration v31

The v31 migration adds these tables:

1. `ai_model_catalog`
2. `ai_model_role_assignments`
3. `ai_prompt_templates`
4. `ai_executions`
5. `ai_execution_payloads`
6. `ai_usage_records`
7. `ai_budget_policies`
8. `ai_cache_entries`
9. `ai_runtime_settings`

The migration is idempotent, non-destructive, and compatible with a new database or an upgrade from v30.

## Table Contracts

### `ai_model_catalog`

Stores provider, model id, snapshot or version, status, capabilities, context limit, pricing, and replacement history.

Canonical statuses:

- `testing`
- `approved`
- `deprecated`
- `unavailable`
- `blocked`

### `ai_model_role_assignments`

Stores global or creator-specific role assignments.

Rules:

- `creator_id = NULL` means global assignment;
- creator-specific rows override global rows;
- only approved or intentionally testing entries should be assigned to active roles.

### `ai_prompt_templates`

Stores versioned prompt templates.

Rules:

- approved templates are immutable;
- a new version is created instead of overwriting an approved one;
- v31 seeds one approved template: `provider_diagnostic` version `1`.

### `ai_executions`

Stores normalized execution records.

Rules:

- no raw secrets;
- no raw headers;
- no audio or video payloads;
- status is normalized;
- request fingerprints and provenance are preserved.

### `ai_execution_payloads`

Stores diagnostic payload artifacts only.

Initial payload types:

- `prepared_request`
- `provider_response`
- `validated_result`
- `validation_report`

### `ai_usage_records`

Stores per-attempt usage and cost records.

Supports:

- retries;
- repairs;
- fallback;
- future comparison workflows.

### `ai_budget_policies`

Stores scoped monthly, daily, and per-task policies.

Minimum enforced in v31:

- `monthly_limit`
- `per_task_limit`
- `hard_block_enabled`

### `ai_cache_entries`

Stores exact cache hits for diagnostic requests.

Policies:

- `use`
- `bypass`
- `refresh`

### `ai_runtime_settings`

Stores non-secret runtime settings.

Examples:

- `provider_enabled`
- `preferred_currency`
- `max_retries`
- `cross_provider_fallback_enabled`
- `cost_approval_threshold`
- `default_privacy_class`
- `env_credentials_enabled`

## Request And Result Contracts

### `AIExecutionRequest`

Supported in v31:

- `task_type = provider_diagnostic`
- `operation = extract`
- `quality_level = standard`
- `privacy_class = selected_text_allowed`

Other task types remain paused.

### `AIExecutionResult`

The normalized result contains:

- execution id;
- request id;
- provider;
- model id and version;
- model role;
- structured result;
- validation;
- usage;
- cost;
- latency;
- cache state;
- fallback state;
- warnings;
- error details;
- provenance;
- timestamps.

## Provider Diagnostics

The foundation exposes a minimum diagnostic flow:

- configure OpenAI or Anthropic credentials;
- store them through the OS credential backend when available;
- assign or resolve a model role;
- run a minimal request;
- validate the response;
- persist usage and execution records;
- report latency, cost, cache, and safe errors.

Diagnostics must work with:

- only one provider configured;
- no provider configured, where the app still opens and reports the missing state.

### Request Profiles

Provider request compatibility is resolved centrally through versioned request profiles.

Current v31 rules:

- OpenAI diagnostics use the Chat Completions endpoint for the approved v31 flow.
- gpt-5.6-luna uses max_completion_tokens on Chat Completions and does not send max_tokens.
- gpt-5.6-luna omits temperature in the minimal connectivity diagnostic; temperature is only sent when a profile explicitly permits it and the request truly needs it.
- OpenAI structured output support is handled through the request profile, not through GUI conditionals.
- Anthropic retains its own request profile and output-token parameter contract.
- The catalog version for request-profile decisions is stored as v31-request-profiles-2026-08-06.

The request-profile layer is intentionally central so that endpoint and parameter exceptions are not duplicated across GUI, service, and provider code.
The provider adapter validates the final serialized OpenAI payload before HTTP, and the contract fake is strict about unsupported fields so the repository does not keep rediscovering the same parameter mismatch one call at a time.
Execution identity is split into three distinct values:

- `request_id` identifies one concrete attempt and is unique per run;
- `execution_uuid` identifies the persisted execution row and is unique per row;
- `request_fingerprint` identifies the semantic request shape and may repeat across historical executions.

Fingerprint rules:

- the fingerprint excludes per-run control values such as `request_id`, `cache_policy`, `fallback_policy`, and `approval_policy`;
- `use` may reuse a valid cached execution when the semantic fingerprint matches;
- `bypass` and `refresh` always start a new execution, but they may share the same historical fingerprint as prior attempts;
- only active executions block a duplicate diagnostic while a run is still in progress.

### Approval Workflow

When the budget policy determines that a diagnostic needs approval, the execution pauses in `awaiting_approval` instead of failing validation.

Rules:

- `awaiting_approval` means the execution is paused for a human decision;
- the validation status for that state is `requires_human_review`, not `rejected`;
- the GUI must surface provider, model, role, reason, estimated cost, currency, scope, and the policy that triggered approval;
- approval is per execution, not global;
- approval metadata must record who approved, when, the approval reason, the estimated cost at approval, and the provider/model at approval;
- approval is invalidated if the provider, model, privacy decision, or estimated cost changes materially before resume;
- rejection must cancel the execution, skip the provider call, and preserve a safe trace in history;
- price unknown is not treated as zero;
- when pricing is not verified, the UI must say so explicitly and allow a manual approval for the minimal diagnostic path;
- history must show pending approval, approved, rejected or cancelled states, along with the actor, date, reason, provider, model, and whether pricing was unknown;
- approval does not create a second execution row;
- the persisted row keeps the same `execution_uuid`, `request_id`, and `request_fingerprint` from creation through completion;
- `create_execution(request)` creates a fresh row, while `resume_approved_execution(execution_uuid)` continues the same row after approval;
- `Aprobar y continuar` must disable approval controls immediately, persist approval on the existing row, validate the approval context, and resume the same execution in the background;
- if resume cannot proceed, the UI must fail visibly instead of leaving an `awaiting_approval + approved` mismatch on screen.

### Button States

- `awaiting_approval`: show `Aprobar y continuar`, `Rechazar`, and `Revisar presupuesto`; `Cancelar ejecucion activa` is optional only when the execution is still live.
- `approved`, `preparing_context`, `running`, `validating`: hide the approval buttons and show cancel only while a live worker or lease still exists.
- `completed`, `failed`, `cancelled`, `rejected_by_user`, `interrupted`: hide the approval controls and hide `Cancelar ejecucion activa`.
- button visibility must follow `status` plus live worker state, not the mere presence of an `execution_id`.

### Idempotence

- double clicks on approval must produce one persisted approval and one provider call;
- the same execution must not get a second `execution_uuid` or `request_id` just to continue after approval;
- if the app reopens while approval is pending or the worker is live, it must restore the same execution and continue or recover safely without creating a duplicate;
- if provider, model, privacy, or materially relevant cost changes before continuation, the approval must be invalidated and the execution marked with a safe reason.

### Execution Recovery

AI runtime executions keep the same persisted row across approval, retry, cancellation, and recovery.

Recovery rules:

- `queued`, `preparing_context`, `running`, and `validating` are active states only while a live worker or task lease still exists;
- `awaiting_approval` is recoverable and must remain visible after restart so the same execution can be approved or rejected;
- `approved` is a brief resume marker on the same row and must not become a second execution;
- a startup recovery pass reconciles orphaned active rows and marks stale rows as interrupted or cancelled with a safe reason;
- the app must not call the provider automatically during recovery;
- the app must not create a duplicate execution just to report that one already exists;
- a live execution is the one that still has a recognized task or worker heartbeat, or is waiting for human approval;
- a stale or interrupted execution can be retried, but a live one must block duplicate provider calls;
- legacy linked continuation rows remain readable, but new approvals do not create them.

Cancellation and retry:

- canceling an active AI runtime execution keeps the row in history and records the actor and time;
- cancellation should clear the active fingerprint so a later retry can create a new attempt;
- retry after `cancelled`, `interrupted`, `failed`, or `rejected_by_user` creates a new execution attempt linked to the same semantic request;
- retry after recovery must not reuse a still-live execution row.

### Price Unknown

- an unknown price must stay unknown; it can be approved manually, but it must not be converted to `0` as a verified cost;
- the UI must show that pricing is not verified when approval is required for that reason;
- if the provider returns no verified price, the visible calculated cost remains `No disponible` unless a verified price later appears.

Credential validation and model catalog synchronization are separate steps:

- validation confirms the stored credential can reach the provider;
- synchronization queries the provider model endpoint, normalizes the response, and updates `ai_model_catalog`;
- a valid credential does not imply the local catalog is populated;
- role assignment and diagnostic resolution only use synchronized catalog entries.

## Credentials

Rules:

- never store API keys in SQLite;
- never store them in logs or backups;
- use the OS credential backend when available;
- Windows Credential Manager is the primary backend;
- a development env fallback exists only when explicitly enabled;
- the app never exposes the full key after storage.

## Privacy

The privacy engine returns:

- decision;
- allowed providers;
- allowed modalities;
- required redactions;
- approval requirement;
- reasons;
- blocked fields.

Canonical decisions:

- `allowed`
- `allowed_with_redaction`
- `requires_approval`
- `blocked`

## Budget

The budget policy can block execution before the provider is called.

Rules:

- no silent overflow;
- hard block is allowed;
- approvals must be invalidated when provider, model, or cost changes materially;
- the execution record must show the safe reason for a block.

## Cost

The cost estimator and tracker are intentionally conservative.

Tracked data:

- estimated minimum and maximum cost;
- provider-reported cost when available;
- calculated cost;
- tokens by usage class;
- retries;
- cache hits;
- aggregation by provider, model, task, and period.

## Cache

The cache is exact-match only.

Rules:

- do not collapse intentional variants;
- support bypass and refresh;
- preserve the original fingerprint;
- keep cache entries traceable to the execution they reuse.

## Errors

Canonical normalized categories:

- `authentication_error`
- `authorization_error`
- `billing_error`
- `rate_limit_error`
- `quota_error`
- `model_unavailable`
- `model_deprecated`
- `invalid_request`
- `invalid_response`
- `schema_validation_error`
- `privacy_block`
- `budget_block`
- `timeout`
- `network_error`
- `provider_error`
- `cancelled_by_user`
- `internal_error`

Every error must expose a safe message, a retry flag, and a suggested action.

## Retries And Repair

Retries:

- maximum 2 automatic retries;
- only for timeout, network, rate limit, or temporary provider errors;
- never for billing, quota, privacy, invalid request, or user cancelation.

Repair:

- one local safe repair attempt is allowed;
- repair only for simple formatting issues;
- never use repair to invent evidence.

## CLI

The foundation adds:

- `python -m creator_intelligence_studio ai --help`
- provider listing and status
- provider tests
- model listing and verification
- role assignment
- budget inspection and updates
- diagnostic execution
- execution history

API keys are not passed as CLI arguments.

## GUI

The desktop shell now exposes a dedicated `AI Runtime` page in the sidebar. The old system summary remains a technical overview, but it is not the primary entry point for provider setup or diagnostics.

Visible categories:

- provider status;
- model and role mapping;
- budget and consumption;
- diagnostics;
- execution history.

Model selectors in the runtime page are populated from the synchronized catalog. If no compatible models are available yet, the page explains that the user must validate the credential and refresh the provider catalog first.

The catalog is not reduced in storage. The selector applies conservative presentation rules:

- recommended models appear first;
- compatible models follow;
- advanced snapshots and previews are hidden by default;
- deprecated, unavailable, blocked, and incompatible entries are only shown in the explicit `Mostrar todos los modelos` mode;
- searches filter the current presentation only and do not alter the catalog itself;
- existing assignments remain visible even if they are no longer the preferred choice.

Recomendations are advisory only:

- the service computes them from catalog metadata, role constraints, status, pricing, and verification recency;
- the UI never silently replaces a stored assignment with a newer recommendation;
- missing pricing or verification data is shown as `Compatible, pendiente de evaluacion` instead of being guessed.
- provider discovery is treated conservatively; capability keys with false values do not turn a model into an unsupported special case, and only the verified current-family rules feed the guided recommendation path.

Guided configuration is now the default entry point for `Modelos y roles`:

- the default view is `Configuracion recomendada`;
- the mode selector stays visible in both recommended and advanced views;
- the user can return to `Configuracion recomendada` at any time without leaving the page;
- switching modes does not save assignments or change models automatically;
- the guided panel shows the provider, last sync time, catalog size, compatibility state, profile, and warnings;
- the `EconÃ³mico`, `Equilibrado`, `MÃ¡xima calidad`, and `Personalizado` profiles are resolved by a dedicated recommendation component;
- only `cheap_structured_model` is required in v31 for the diagnostic path;
- the remaining roles are shown as not required in the current phase instead of being treated as mandatory.
- when the synchronized catalog includes a verified current OpenAI family entry, the balanced profile proposes a concrete `cheap_structured_model` instead of falling back to the legacy GPT-3.5 assignment.

The recommended resolver uses a curated local compatibility matrix that is versioned independently from provider discovery:

- discovery still comes from the provider `/models` endpoint;
- missing metadata is treated as `compatibility_unknown`, not as a confirmed incompatibility;
- `compatibility_unknown` stays out of the recommended path but can still be surfaced in advanced mode;
- `incompatible_confirmed` is reserved for explicit evidence such as blocked status, deprecated status, or known role conflicts;
- the UI can apply the recommended configuration after a confirmation step, and it preserves custom assignments when the user declines a replacement.

Advanced manual selection remains available:

- it is hidden behind `Configuracion avanzada`;
- a dedicated `Volver a configuracion recomendada` control is available at the top of the advanced panel;
- search, snapshots, previews, and full catalog browsing remain available there;
- the advanced selector is no longer the default path for a normal user.

## Task Center

Diagnostic work can appear as `ai_runtime_diagnostic`.

The Task Center must treat it as a normal background task with safe status and retry behavior.

For AI runtime diagnostics it should show the persisted execution identity, provider, model, status, and last activity, and it should allow:

- opening the active execution details;
- canceling a live execution when the worker or lease still exists;
- retrying only after an execution is stale, interrupted, cancelled, failed, or rejected.

## Security Limits

Do not add:

- corpus learning;
- embeddings;
- semantic retrieval;
- automatic video editing;
- publication automation;
- third providers;
- fixed model names inside product modules;
- secret storage in SQLite;
- silent cross-provider fallback;
- collective data sharing without consent.

## Tests

The foundation is covered by tests for:

- provider normalization;
- orchestrator policies;
- request-profile resolution and validation;
- strict OpenAI payload contracts;
- credential storage;
- cost tracking;
- template immutability;
- persistence;
- CLI wiring;
- diagnostics;
- integration with a fake provider;
- migration v31.

Live provider tests are opt-in only.

## Next Phase

The next approved block after this foundation is:

`Component Manager and Local Transcription Foundation`

That stage may improve installation and local transcription ergonomics, but it does not replace the AI runtime contract defined here.

## Post-Implementation Verification

This section records what was verified during the v31 closeout audit.

### Verified by mocks

- OpenAI HTTP contract, including method, URL, headers, timeout, body shape, structured output handling, usage extraction, error mapping, and sanitization.
- Anthropic HTTP contract, including method, URL, headers, required API version header, timeout, body shape, content extraction, usage extraction, error mapping, and sanitization.
- Orchestrator policy behavior for privacy, budget, retries, repair, cache reuse, duplicate detection, disabled providers, missing credentials, and model resolution.
- CLI command wiring for AI runtime commands.

### Verified by local integration

- SQLite v31 migration on a fresh database and from a v30 schema seed.
- Credential round-trip behavior with the in-memory backend used in tests.
- Workspace view-model wiring for AI runtime status, credentials, tests, roles, budgets, diagnostics, and history.
- Desktop CLI execution with `python -m creator_intelligence_studio --diagnostic-json`.
- Interactive GUI startup via `scripts/run_gui.bat`, which clears inherited test variables before launching a visible desktop window.
- Offscreen GUI startup and auto-exit are reserved for `scripts/run_gui_test.bat` with `CIS_GUI_TEST_MODE=1`.
- The desktop shell now shows the main window before deferred AI Runtime recovery and `refresh_all()`, so a slow local section cannot block window presentation.
- `AIRuntimeOverviewView` restores the current diagnostic state without recursively refreshing the whole page, preventing startup loops.
- Dedicated desktop navigation into the `AI Runtime` page from the sidebar.
- Reversible navigation between recommended and advanced model configuration panels without mutating assignments.
- Real GUI tab presence for providers, roles, budget, diagnostics, and history.
- A navigation smoke test that clicks the sidebar entry and verifies the mounted page.
- Provider credential validation followed by catalog synchronization into `ai_model_catalog`.
- GUI model selection populated from synchronized provider models and role assignment persistence.
- The OpenAI discovery path was corrected to avoid treating every normalized model as audio-capable or otherwise incompatible just because the provider metadata includes false boolean keys.
- The v31 repair path now normalizes `ai_executions` so `request_fingerprint` is indexed but not globally unique, preserving historical rows while allowing repeated diagnostics.
- The diagnostics button now launches a background `QThread`, disables the button immediately, shows `Preparando diagnÃ³sticoâ€¦`, and re-enables the UI when the run finishes.
- Successful and failed diagnostics both refresh the visible execution fields and the history table without exposing secrets or raw provider payloads.
- Duplicate clicks are blocked while the diagnostic thread is active, and the Task Center background task entry is created by the workspace view-model before the provider call begins.

### CredentialStore mechanism

- Windows uses the real Windows Credential Manager backend through `CredWriteW`, `CredReadW`, `CredDeleteW`, and `CredFree`.
- The stored target name is stable and creator-safe: `ai.<provider>.api_key`.
- A pure in-memory backend exists for tests.
- An explicit development environment backend exists only when `CIS_ENABLE_ENV_CREDENTIALS=1`.
- No API key is stored in SQLite or JSON by this foundation.

### Current limitations

- Provider behavior is still verified with HTTP mocks; no production provider call was made in this audit.
- Live tests remain opt-in and are skipped unless `CIS_RUN_LIVE_AI_TESTS=1`.
- The foundation remains intentionally narrow: provider diagnostics and orchestration only.
- The new desktop page is configuration and diagnostics only; it does not add creative generation flows.
- Model capabilities remain conservative when the provider response does not report enough evidence.
- Pricing may remain marked as pending verification until the provider data is synchronized.
- The selector intentionally hides snapshots, previews, and technical variants by default to keep role assignment safe and readable.
- The diagnostics view does not call the provider on the GUI thread; it uses the existing background-task pattern so the window stays responsive while the execution is running.
- If the provider raises before an execution result exists, the GUI shows a safe failure message and re-enables the button instead of swallowing the exception.

### Test coverage added or confirmed

- Full repository suite: 219 tests passed, 2 skipped.
- AI runtime-focused suite: credentials, providers, orchestrator, cache, repository, migration, CLI, GUI, and live opt-in placeholder.
- Provider-specific coverage includes success paths, authentication, authorization, billing, quota, rate limits, malformed JSON, timeouts, and connection failures.
- Orchestrator coverage includes privacy blocking, budget blocking, cache exact hits, cache bypass, cache refresh, duplicate active requests, retries, repair, and safe persistence.
