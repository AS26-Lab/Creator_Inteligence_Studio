# Subtitle Deliveries

Creator Intelligence Studio supports two local subtitle delivery modes for clip renders:

- `sidecar_srt` / `sidecar_vtt`: keep the MP4 unchanged and export a verified subtitle file alongside it.
- `burn_in`: render a new MP4 with subtitles visually embedded through FFmpeg and libass when available.

## Principles

- Deliveries are local and reproducible.
- A delivery stores a snapshot of the subtitle track version, fingerprint, cue count, format, and style.
- Subtitle tracks remain editorial artifacts; deliveries do not rewrite the source transcription.
- Render history stays valid even if the underlying subtitle track changes later.

## Safety

- Subtitle text is treated as text, not as ASS code.
- Sidecar exports are verified with round-trip parsing.
- Burn-in renders use a managed temporary ASS file and a managed output path.
- Delivery outputs are optional and do not change ranking, personalization, or training.

## Limits

- No translation.
- No diarization.
- No karaoke.
- No animated subtitle styles.
- No automatic publication.
