# Grounded AI Workflow Architecture

## Boundary

Creator Corpus grounding is a distinct boundary between:

1. local retrieval
2. context assembly
3. AI request construction
4. provider execution

Provider adapters do not perform retrieval directly.

## Trust Hierarchy

The request stack keeps these layers separate:

1. system policy
2. current user request
3. primary user artifact, when present
4. creator context from corpus
5. provider execution

Corpus text is data, not instruction authority.

## Context Policies

Workflow-specific policies define:

- whether context is allowed
- whether it is required, preferred, optional, or forbidden
- which document types are eligible
- which authorship classes are eligible
- the budget allocated to context
- whether provenance is included
- whether historical versions are allowed

## Context Bundle

The assembler returns structured bundles with:

- bounded items
- categories
- authorship labels
- provenance
- snippets
- estimated size
- truncation metadata

That bundle is rendered later into a deterministic prompt block.

## Budgeting

Context budgets are allocated per workflow and remain bounded.

The assembler may trim or omit lower-priority items, but it does not expand past the allocated budget.

## Safety

- corpus text is untrusted data
- prompt injection strings remain quoted as evidence
- cross-creator leakage is forbidden
- context-off mode is explicit
- empty corpus is valid for preferred workflows
- diagnostics stay context-free
