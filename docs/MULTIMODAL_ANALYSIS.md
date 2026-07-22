# Multimodal Analysis

## Purpose

The multimodal layer aligns existing technical outputs from transcription, acoustic analysis, and visual analysis into a shared timeline.
It is local, deterministic, and evidence-driven.

It does not select final clips.
It does not predict virality.
It does not infer emotions as facts.
It does not replace the source analyses.

## Sources

- transcription segments and timestamps;
- acoustic windows, pauses, energy, and acoustic candidates;
- visual windows, scenes, cuts, keyframes, and visual events.

The layer can operate with partial coverage.
Missing sources reduce confidence and are reported as warnings.

## Temporal alignment

Initial configuration:

- base windows: 1 second;
- context windows: 5 seconds;
- candidate fusion range: 3 to 30 seconds;
- tolerance for nearby events: configurable.

The most reliable source duration is used as the reference timeline length.
The layer handles missing windows, slightly different durations, partial analyses, and sources that stop at different timestamps.

Text is never interpolated.

## Normalization

Signals are normalized within each video before scoring.
Robust methods are preferred:

- percentiles;
- medians;
- median absolute deviation;
- outlier bounds;
- 0 to 1 scaling.

Original values remain available when they are useful for evidence.
Normalized values are used for cross-modal comparison.

## Window features

Per window, the layer tracks:

- transcript text and word count;
- speech presence and silence ratio;
- speech rate and relative speech change;
- acoustic energy and acoustic change;
- visual motion and visual change;
- brightness;
- cut count;
- scene index;
- acoustic event count;
- visual event count;
- combined activity score;
- transition score;
- novelty score;
- confidence;
- evidence JSON.

## Scoring

Scores are transparent and configurable.

Current structure:

- `combined_activity_score`
  - acoustic energy weight;
  - speech rate weight;
  - visual motion weight;
  - cut weight;
  - event weight.
- `transition_score`
  - acoustic change;
  - visual change;
  - cut signal.
- `novelty_score`
  - distance from nearby context activity.
- `confidence`
  - coverage of available sources;
  - agreement between sources;
  - strength of the strongest signal.

Scores are not probabilities.

## Candidate types

Technical candidate categories:

- `high_combined_activity`
- `abrupt_multimodal_change`
- `speech_energy_peak`
- `visual_transition_with_speech`
- `long_silence_or_pause`
- `low_activity_segment`
- `acoustic_event_with_visual_change`
- `scene_opening`
- `scene_closing`
- `possible_hook_candidate`
- `possible_reaction_candidate`
- `unknown_candidate`

The last two are heuristic placeholders, not semantic classification.

## Candidate fusion

Nearby candidate seeds are merged deterministically.

Rules:

- avoid many overlapping candidates;
- preserve evidence from all merged seeds;
- enforce minimum and maximum duration bounds;
- split overly long clusters;
- order by time and score;
- keep output stable for the same inputs.

## Evidence

Each candidate stores evidence built from real measurements.
Examples:

- acoustic energy at a high percentile;
- speech rate above the median;
- multiple cuts in a short span;
- high visual motion;
- nearby acoustic event candidate;
- scene boundary;
- silence duration.

Evidence is technical.
It does not contain invented LLM prose.

## Stale

Multimodal analysis becomes stale when any of these change:

- transcription;
- acoustic analysis;
- visual analysis;
- configuration;
- analyzer version;
- fingerprints;
- associated cache.

Partial operation is allowed when a source is missing, but warnings are recorded and confidence is reduced.

## Persistence

Migration v7 adds:

- `multimodal_analyses`
- `multimodal_timeline_windows`
- `multimodal_moment_candidates`

Structured storage is used for:

- status;
- source references;
- durations;
- scores;
- confidence;
- counts;
- evidence JSON;
- warnings and errors.

This layer is intentionally separate from the source analyses.

## CLI

- `multimodal analyze --video-id <id>`
- `multimodal analyze --video-id <id> --force`
- `multimodal show --video-id <id>`
- `multimodal timeline --video-id <id>`
- `multimodal candidates --video-id <id>`
- `multimodal candidate --candidate-id <id>`
- `multimodal export --video-id <id> --format json`
- `multimodal export --video-id <id> --format timeline-csv`
- `multimodal export --video-id <id> --format candidates-csv`
- `multimodal export --video-id <id> --format txt`
- `multimodal delete --video-id <id>`

## GUI

The desktop UI exposes a multimodal timeline view from the selected video.

It shows:

- status and analyzer version;
- available and missing sources;
- stale state;
- synchronized windows;
- candidate list;
- timeline tracks;
- evidence;
- export and delete actions.

The UI does not access source internals directly.

## Privacy

- Processing is local.
- No audio, video, or text is uploaded.
- No private content is stored in docs.
- No final clip decision is made here.

## Current limitations

- No final clip selection.
- No narrative interpretation.
- No retention prediction.
- No LLM layer.
- No personalized learning yet.

## Clip ranking handoff

The multimodal layer is the technical source for the clip ranker.

- It provides aligned windows, candidate timestamps, evidence, and stable ordering.
- The clip ranker adds human review, overlap resolution, diversity, and export planning.
- Multimodal scores remain separate from clip ranking scores.
- A multimodal candidate can map to multiple future review states, but it is not deleted when a clip is rejected.
