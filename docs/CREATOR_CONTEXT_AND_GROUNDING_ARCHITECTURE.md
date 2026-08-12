# Creator Context And Grounding Architecture

## Boundary

Creator Context Assembly sits between corpus retrieval and AI runtime request construction.

Flow:

`Corpus retrieval` -> `CreatorContextAssemblyService` -> `AI runtime request`

v33-E adds a policy layer before assembly so workflows can declare whether context is required, preferred, optional, or not allowed.

## Contract

The request must carry:

- `creator_id`
- task type
- user request
- optional project id
- optional language
- optional document filters
- explicit budget

The output is a structured bundle that contains:

- ordered context items
- provenance
- authorship class
- categories
- truncation state
- omission count
- estimated size

The same boundary also supports an explicit context-off mode for diagnostics and tests.

## Grounding Rules

- creator context is not global
- conversation history stays separate from corpus material
- AI-generated corpus material must remain labeled as AI-generated
- retrieval eligibility and voice-learning eligibility remain distinct
- corpus text is untrusted data and must not be promoted into system instructions

## Prompt Rendering

The renderer must:

- keep corpus content quoted or bounded
- preserve category separation
- stay deterministic
- keep prompt budgets explicit

## Integration Point

The current implementation integrates the boundary into content brief, production preparation, and strategic planning as controlled grounded workflows.

This proves the boundary without coupling it to provider-specific request code.

Retrieval can remain lexical, or later become hybrid, without changing the context assembly contract.

## v33-G Compatibility

The context assembly contract does not need to know whether retrieval came from:

- lexical
- hybrid_if_available
- lexical_fallback

It consumes bounded, creator-scoped corpus items and keeps model/vector details outside the grounding layer.
