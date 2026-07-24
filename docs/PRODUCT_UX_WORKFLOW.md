# Product UX Workflow

This document describes the first integrated desktop experience for Creator Intelligence Studio.

## Goal

Let a person work from a creator and project context without needing internal IDs, table names, fingerprints, or CLI commands.

The UX exposes:

- creator and project selection;
- video import and review;
- a recommended next action per video;
- a task center for background work;
- onboarding and system health;
- preferences for local folders and transcription behavior.

## Main flow

1. Home
2. Select creator
3. Select project
4. Import video
5. Inspect and prepare
6. Run the next recommended step
7. Review clips
8. Provide feedback
9. Render approved clips when desired
10. Prepare subtitles when useful
11. Monitor personalization
12. Reopen the app and continue

## Pipeline status

The workflow page aggregates public service state into a per-video pipeline status.

It shows:

- current stage;
- recommended action;
- overall status;
- approximate progress;
- warnings and block reasons;
- stage-by-stage summaries.

The aggregated status does not duplicate core analysis logic.

Rendering is optional and local. It becomes available after review when a clip is approved or explicitly selected, but it does not replace the personalization workflow.
Subtitle preparation is also optional. It can follow a transcription or a clip review, but it does not change the source transcription and it is not required for ranking, personalization, or rendering without subtitles. When the user wants delivery with subtitles, the system can produce a sidecar file or a new burn-in MP4 from the chosen track.

## Task Center

Background tasks are persisted in local UI state so they remain visible after navigation changes and after reopening the app.

Interrupted tasks are shown as interrupted and can be retried from the workflow page.

## Error handling

User-facing errors are translated into short explanations with an optional technical detail section.

The main interface avoids raw stack traces and explains why an action is unavailable.

## Stale results

Stale means the result belongs to an older version of the video or derived artifact.

The UI should offer:

- refresh;
- inspect what changed;
- keep the prior result;
- remove the stale result when appropriate.

## Preferences

The initial UX preferences are local and reversible:

- data folder;
- model folder;
- export folder;
- preferred transcription device;
- transcription profile;
- ranking profile;
- confirmation behavior;
- technical detail visibility.

## Limitations

- This workflow does not render clips.
- This workflow does not require subtitles for the main pipeline, although subtitle delivery is available as a separate optional step.
- This workflow does not auto-train a model.
- A successful run proves technical coherence, not predictive or commercial quality.
- Existing data is not moved automatically when a new folder preference is selected.

## Analytics workflow

- seleccionar creador;
- seleccionar o crear canal;
- elegir plataforma;
- inspeccionar archivo CSV o XLSX;
- revisar schema y mappings sugeridos;
- corregir mappings manualmente si hace falta;
- importar;
- revisar publicaciones y snapshots;
- exportar datos normalizados.

This flow records observed facts. It does not infer causality, predictions, or recommendations.
