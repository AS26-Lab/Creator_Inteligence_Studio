# Clip Rendering

## Scope

This first version renders approved or explicitly selected clips locally with FFmpeg.

It is:

- local;
- reproducible;
- verifiable;
- non-destructive;
- cancelable;
- batch-aware for collections.

It does not:

- publish to platforms;
- edit multi-track timelines;
- add burned-in subtitles;
- do smart vertical reframing;
- add automatic music or generative transitions.

## Profiles

- `source_quality`: highest quality, larger file, preserve source characteristics when possible.
- `balanced`: default profile, H.264 + AAC, balanced quality and size.
- `compact`: smaller output, lower resolution when appropriate.
- `draft`: faster review render, reduced resolution and quality.

## Output and verification

- MP4 container by default.
- H.264 video and AAC audio by default.
- Temporary files use a managed `.part.mp4` pattern before atomic rename.
- Each completed job stores verification metadata from `ffprobe`.
- A completed output is not reused unless the verified artifact matches the source and configuration fingerprint.

## UX

- Render actions appear in Clip Candidates and Collections.
- Render jobs are persisted in the Task Center.
- The workflow page may recommend rendering approved clips after review.
- Rendering is optional and does not replace personalization readiness.

## Data model

Render history is stored in migration v12:

- `clip_render_jobs`
- `clip_render_artifacts`
- `clip_render_events`
- `clip_render_batches`
- `clip_render_batch_items`

## Limitations

- No publication flow yet.
- No full video editor yet.
- No distributed rendering yet.
- No GPU encoding requirement.
