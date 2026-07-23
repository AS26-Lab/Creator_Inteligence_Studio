# Subtitles

## Scope

The local subtitle layer turns an existing transcription into editable subtitle tracks.

It is:

- local;
- reproducible;
- versioned;
- non-destructive to the source transcription;
- suitable for full videos and clip-relative tracks.

It does not:

- translate automatically;
- perform diarization;
- burn subtitles into video yet;
- replace the transcription engine;
- auto-correct creator wording or tone.

## Core distinction

- The transcription captures what the engine detected.
- Subtitle tracks are editorial artifacts built from that transcription.
- Editing a subtitle cue does not rewrite the original transcription.

## Source types

- `transcription_generated`
- `clip_generated`
- `imported_srt`
- `imported_vtt`
- `imported_ass`
- `manual`

## Generation

Subtitle tracks can be generated for:

- a full video, using absolute timestamps from the transcription;
- a clip candidate, using clip-relative timestamps while preserving absolute source timestamps as metadata.

Generation is deterministic and uses configurable segmentation rules for cue length, line wrapping, pause-aware splits, and readable timing.

## Editing

The first version supports:

- update cue text;
- update cue timing;
- split and merge cues;
- insert, delete, move and shift cues;
- lock, unlock, duplicate, archive and restore tracks.

Edits are stored as history events so the track can be audited and compared later.

## Validation

Each cue is checked for:

- chronological order;
- overlap;
- bounds;
- duration limits;
- line limits;
- character density;
- empty text;
- duplicate text;
- estimated timing warnings.

Warnings do not block export by themselves. Invalid cues do.

## Import and export

Supported import formats:

- SRT;
- WebVTT;
- basic ASS.

Supported export formats:

- SRT;
- WebVTT;
- ASS;
- TXT;
- JSON.

Exports are written to a managed local folder and verified after creation.

## Clip-relative timing

For clip tracks:

- `0` means the start of the final clip;
- absolute source timestamps are preserved as metadata;
- cues that cross the clip boundary are trimmed to the usable range;
- a later bounds change marks the track stale.

## Stale

A subtitle track becomes stale when its source transcription, source video, clip bounds, segmentation configuration, or generator version changes.

Stale tracks are preserved for audit and comparison. They are not silently overwritten.

## UX

Subtitle generation and import/export can appear as background tasks.
Manual cue editing stays interactive and local.

The workflow can surface an optional next action such as preparing subtitles, but subtitles are not required for analysis, ranking, personalization, or clip rendering.

## Limitations

- No burned-in subtitles yet.
- No translation yet.
- No live playback editor yet.
- No automatic content rewriting.
- No automatic profanity replacement.

