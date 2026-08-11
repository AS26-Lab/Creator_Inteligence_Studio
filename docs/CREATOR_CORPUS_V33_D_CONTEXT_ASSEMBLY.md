# Creator Corpus v33-D Context Assembly

## Scope

v33-D adds the canonical local boundary that turns Creator Corpus retrieval results into grounded AI context.

This phase:

- requires an explicit `creator_id`
- reuses `CreatorCorpusRetrievalService`
- assembles structured context items before prompt rendering
- preserves provenance, authorship class, project context, and budget limits
- keeps corpus text as untrusted data
- keeps conversation history separate from corpus context

## What It Is

The implemented service is `CreatorContextAssemblyService`.

Its responsibilities are:

- choose deterministic retrieval queries from the caller task type and creator context
- deduplicate overlapping retrieval hits
- group nearby transcript segments
- classify items into categories such as:
  - `creator_evidence`
  - `project_context`
  - `reference_material`
  - `ai_generated_context`
- preserve provenance and source identity
- enforce a bounded context budget
- render prompt text with explicit untrusted-data framing

## What It Is Not

v33-D does not implement:

- embeddings
- vector search
- LLM retrieval
- prompt generation from the corpus directly inside providers
- feedback learning
- voice learning
- semantic ranking

## Integrated Workflow

The first safe integration target is the content brief snapshot workflow.

That path now captures:

- a structured context bundle
- a diagnostic context package
- a deterministic prompt rendering

This is intentionally narrow. The same boundary can be reused by future AI request builders without coupling corpus retrieval to provider implementations.

## Security Boundary

Corpus content is treated as data, not instructions.

Prompt rendering must keep the corpus content delimited and untrusted so corpus text cannot become system instruction content.

## Current Limitation

The assembly layer is grounded and local-only. It does not yet perform semantic retrieval or reasoning over corpus text.
