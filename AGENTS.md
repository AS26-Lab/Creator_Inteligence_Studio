# AGENTS.md

## Repository Rules For Future Agents

Before proposing or implementing any new phase, read:

1. `docs/PROJECT_BIBLE.md`
2. `docs/AI_ML_ARCHITECTURE.md`
3. `docs/AI_IMPLEMENTATION_ROADMAP.md`
4. `docs/DECISION_REGISTER.md`
5. `docs/AI_RUNTIME_AND_PROVIDER_ORCHESTRATION_FOUNDATION.md` when touching AI runtime work
6. The module-specific documentation for the area being changed

## Hard Constraints

- Do not add new phases outside the approved roadmap without explicit approval.
- Do not change the product pillars or redefine the scope silently.
- Do not implement automatic video editing.
- Do not add additional normal provider integrations during the initial AI stage.
- Do not call OpenAI or Anthropic directly from product modules; route through the AI orchestrator.
- Do not hard-code fixed models into product logic; use replaceable roles.
- Do not persist MP4 files permanently by default.
- Do not mix data between creators.
- Do not send collective data without explicit consent and revocation support.
- Do not depend on remote provider memory as a product source of truth.
- Default AI runtime and product flows must be guided and plain-language for non-technical users; put technical controls behind explicit advanced modes instead of expecting users to decode internals.

## Decision Handling

- If a documentation or implementation request conflicts with the Project Bible, the latest approved decision wins.
- Contradictions must be documented, not hidden.
- The canonical order of authority is the one stated in `docs/PROJECT_BIBLE.md`.
