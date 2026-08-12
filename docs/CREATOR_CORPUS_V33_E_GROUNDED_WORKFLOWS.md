# Creator Corpus v33-E Grounded Workflows

## Purpose

v33-E defines which AI workflows receive creator-corpus context, how much they receive, and which workflows must stay context-free.

The corpus remains untrusted data. This phase only controls grounding policy and prompt assembly.

## Policy Registry

The current registry centralizes workflow policy instead of scattering prompt rules across services.

| Workflow | Grounding mode | Context use | Notes |
|---|---|---|---|
| `content_brief` | `context_preferred` | yes | Baseline grounded workflow already in use |
| `production_preparation` | `context_preferred` | yes | Uses project and creator evidence for script-oriented preparation |
| `strategic_planning` | `context_preferred` | yes | Uses corpus as supporting evidence, but still works without it |
| `script_revision` | `context_preferred` | policy defined | Reserved for future safe integration of revision flows |
| `provider_diagnostic` | `context_not_allowed` | no | Technical diagnostics must not receive creator corpus context |

## Grounding Rules

- creator context is always creator-scoped
- conversation history stays separate from corpus context
- primary user artifacts stay separate from corpus context
- corpus text is rendered as quoted untrusted evidence
- AI-generated corpus material is labeled explicitly
- empty context is valid for preferred workflows
- diagnostics must not consume corpus context

## Selected Workflows

The current grounded workflows are:

1. Content Brief
2. Production Preparation
3. Strategic Planning

These are the only workflows grounded in this phase. The registry may define additional policies for later safe activation, but they are not all auto-wired.

## Context-Off Mode

The grounded workflows expose an explicit `use_creator_context` switch for tests and diagnostics.

This does not change the normal user flow and does not bypass AI Runtime approvals.
