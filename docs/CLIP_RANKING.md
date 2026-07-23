# Clip Ranking

## Purpose

The clip ranking layer turns multimodal candidates into a reproducible review queue for human selection.
It is deterministic, configurable, and explainable.

It does not predict virality.
It does not render clips.
It does not delete the original candidate.

## Inputs

- multimodal candidates;
- multimodal timeline windows;
- transcription segments when available;
- acoustic and visual source coverage;
- ranking profile and weights;
- human feedback history.

## Ranking profiles

- `balanced`: general purpose blend of speech, motion, novelty, transition and evidence.
- `speech_focused`: favors speech density, speech clarity, and transcript coverage.
- `visual_focused`: favors cuts, scenes, motion, and visual novelty.
- `high_energy`: favors acoustic energy, abrupt changes, and movement.
- `story_beats`: favors openings, closings, transitions, and contextual moments.

Profiles only change weights.

## Score model

The rank score is separate from the multimodal score.

Main factors:

- multimodal source score;
- source confidence;
- combined activity;
- novelty;
- transitions;
- evidence strength;
- speech signal;
- visual signal;
- acoustic signal;
- duration fit;
- overlap penalty;
- silence and low-activity penalties;
- missing-source penalty;
- diversity score.

Scores are normalized before combination.
The score is not a probability of clip success.

## Border adjustment

The ranker suggests improved borders using:

- transcription segment boundaries;
- pauses;
- cuts;
- scene limits;
- acoustic activity;
- visual activity.

The stored candidate keeps:

- original borders;
- suggested borders;
- user-adjusted borders;
- history of changes.

## Overlap and diversity

The ranker identifies:

- duplicates;
- near duplicates;
- nested candidates;
- strong overlaps;
- visually or temporally similar candidates.

Temporal IoU, distance between centers and evidence similarity are used as technical signals.

Diversity keeps the top list from collapsing into near-identical moments.
It is soft, not a forced rewrite of valid candidates.

## Human feedback

Supported review actions:

- approve;
- reject;
- shortlist;
- needs_review;
- rating from 1 to 5;
- note;
- tags;
- border adjustment;
- reset review.

Each change is appended to history.
Rejected candidates are preserved.

## Collections

Collections store human-selected sets of ranked candidates for later export or editing.
They are local and deterministic.

## Stale

A ranking becomes stale when any of these change:

- multimodal analysis;
- source candidates;
- profile;
- weights;
- configuration;
- ranker version;
- source fingerprint.

Human feedback is preserved when a fresh ranking can be matched confidently.

## Export formats

- JSON: ranking run, candidates, scores, explanations and feedback.
- CSV: compact review table.
- EDL: technical cut list style output.

Exports are local and controlled by the user.

## Privacy

- All ranking is local.
- No audio or transcript content is uploaded.
- No private notes are logged in full.
- No final editorial decision is inferred automatically.

## Limitations

- No machine learning ranker yet.
- No per-creator training yet.
- No automatic clip rendering yet.
- No platform analytics yet.

## Downstream personalization data

The clip ranking layer feeds creator-isolated dataset snapshots for future training preparation.

- ranking outputs remain heuristic and explainable;
- human feedback is preserved as history;
- dataset export uses stable candidate identifiers, labels and feature schemas;
- no training happens inside the ranking layer.
