# Creator Context And Grounding Architecture

## Boundary

Creator Context Assembly sits between corpus retrieval and AI runtime request construction.

Flow:

`Corpus retrieval` -> `CreatorContextAssemblyService` -> `AI runtime request`

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

The current implementation integrates the boundary into the content brief snapshot workflow as a safe first step.

This proves the boundary without coupling it to provider-specific request code.
