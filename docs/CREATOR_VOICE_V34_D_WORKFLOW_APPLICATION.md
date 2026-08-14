# Creator Voice v34-D Workflow Application

## Purpose

v34-D introduces a controlled workflow application boundary for Creator Voice.

It is the first phase that may let the synthesized guidance bundle influence a workflow, but only through an explicit opt-in boundary and only where the workflow is approved to consume it.

## What v34-D Implements

- a canonical workflow application request and bundle;
- shadow-first diagnostic integration for comparison;
- gated real application for the approved workflow boundary;
- deterministic rendered guidance when application is enabled;
- explicit omission and override reporting;
- bounded fingerprints for preview and application outputs.

## Application Policy

Creator Voice guidance remains subordinate to:

- system and safety rules;
- the current user request;
- current project or artifact instructions;
- confirmed preferences.

The controlled workflow application boundary may consume guidance only when:

- the workflow is on the allowlist;
- application is explicitly enabled;
- the profile and guidance are ready enough to consume;
- the resulting final request is still bounded and deterministic.

## Shadow First

Shadow integration remains the default diagnostic path for non-approved workflows.

That allows:

- comparing voice on/off behavior;
- validating precedence;
- checking observability without changing the final request.

## Non-Goals

v34-D does not:

- apply Creator Voice globally;
- bypass explicit instructions;
- generate a final model-facing style prompt;
- mutate retrieval or preferences;
- use an LLM to interpret the profile.
