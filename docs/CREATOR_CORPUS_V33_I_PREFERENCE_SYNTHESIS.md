# Creator Corpus v33-I Preference Synthesis

v33-I turns repeated creator feedback into human-reviewable preference candidates.
It does not apply those preferences automatically to prompts, retrieval, or creator voice.

## Implemented

- canonical feedback events remain the source of truth
- deterministic learning signals remain derived state
- preference candidates are synthesized from conservative repeated evidence
- confirmed preferences are stored separately from raw events and candidates
- creators can confirm, edit-and-confirm, dismiss, deactivate, and reactivate preferences
- candidates preserve creator, project, and workflow scope
- evidence remains traceable back to feedback events and diff summaries
- the packaged runtime exposes diagnostic surfaces for validation only

## Not Implemented

- automatic prompt mutation
- retrieval reranking
- creator voice synthesis
- fine-tuning
- LLM-based preference inference
- sensitive-trait inference
- global promotion from project-scoped evidence

## Narrow Taxonomy

- `content_length_preference`

Initial safe values:

- `shorter`
- `longer`

## Human Control

Confirmed preferences are explicit user decisions.
They remain active or inactive until the user changes them.
New evidence can create a review candidate, but it does not silently overwrite a confirmed preference.
