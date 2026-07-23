"""Interfaces de persistencia para subtitulos."""

from __future__ import annotations

from typing import Protocol

from .entities import SubtitleCue, SubtitleEditEvent, SubtitleExport, SubtitleTrack


class SubtitleRepository(Protocol):
    def upsert_track(self, track: SubtitleTrack) -> SubtitleTrack:
        raise NotImplementedError

    def get_track_by_id(self, track_id: str) -> SubtitleTrack | None:
        raise NotImplementedError

    def get_track_by_video_asset_id(self, video_asset_id: str) -> SubtitleTrack | None:
        raise NotImplementedError

    def get_track_by_candidate_id(self, candidate_id: str) -> SubtitleTrack | None:
        raise NotImplementedError

    def get_track_by_render_job_id(self, render_job_id: str) -> SubtitleTrack | None:
        raise NotImplementedError

    def list_tracks_for_video(self, video_asset_id: str) -> list[SubtitleTrack]:
        raise NotImplementedError

    def list_tracks_for_candidate(self, candidate_id: str) -> list[SubtitleTrack]:
        raise NotImplementedError

    def list_tracks_for_render_job(self, render_job_id: str) -> list[SubtitleTrack]:
        raise NotImplementedError

    def upsert_cues(self, track_id: str, cues: list[SubtitleCue]) -> list[SubtitleCue]:
        raise NotImplementedError

    def list_cues(self, track_id: str) -> list[SubtitleCue]:
        raise NotImplementedError

    def get_cue_by_id(self, cue_id: str) -> SubtitleCue | None:
        raise NotImplementedError

    def delete_cues_for_track(self, track_id: str) -> None:
        raise NotImplementedError

    def append_event(self, event: SubtitleEditEvent) -> SubtitleEditEvent:
        raise NotImplementedError

    def list_events_for_track(self, track_id: str) -> list[SubtitleEditEvent]:
        raise NotImplementedError

    def list_events_for_cue(self, cue_id: str) -> list[SubtitleEditEvent]:
        raise NotImplementedError

    def upsert_export(self, export: SubtitleExport) -> SubtitleExport:
        raise NotImplementedError

    def list_exports(self, track_id: str) -> list[SubtitleExport]:
        raise NotImplementedError

    def archive_track(self, track_id: str) -> SubtitleTrack | None:
        raise NotImplementedError

    def delete_track(self, track_id: str) -> bool:
        raise NotImplementedError

