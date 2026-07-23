"""Migraciones SQLite minimas y reales."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3

from creator_intelligence_studio.infrastructure.persistence.database import DatabaseError
from creator_intelligence_studio.infrastructure.personalization_data.feature_extractor import (
    CREATOR_FEATURE_DEFINITIONS,
    CREATOR_FEATURE_NAMES,
    CREATOR_FEATURE_SCHEMA_DESCRIPTION,
    CREATOR_FEATURE_SCHEMA_NAME,
    CREATOR_FEATURE_SCHEMA_VERSION,
)


class MigrationError(DatabaseError):
    """Error al aplicar o validar migraciones."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str

    def apply(self, connection: sqlite3.Connection) -> None:
        raise NotImplementedError


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def migration_1(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creators (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'archived'))
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creators_slug ON creators(slug)")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            project_type TEXT NOT NULL CHECK (project_type IN ('long_form', 'short_form', 'mixed', 'research')),
            status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_creator_id ON projects(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS video_assets (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            source_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            file_modified_at TEXT,
            source_type TEXT NOT NULL CHECK (source_type IN ('local_file', 'platform_import', 'manual_reference')),
            processing_status TEXT NOT NULL CHECK (processing_status IN ('registered', 'queued', 'processing', 'completed', 'failed', 'cancelled')),
            registered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            notes TEXT,
            file_available INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_assets_project_id ON video_assets(project_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_assets_processing_status ON video_assets(processing_status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_assets_source_type ON video_assets(source_type)"
    )


def migration_2(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS video_inspections (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            inspection_status TEXT NOT NULL CHECK (
                inspection_status IN (
                    'not_inspected',
                    'queued',
                    'inspecting',
                    'completed',
                    'failed',
                    'file_missing',
                    'tool_unavailable',
                    'stale'
                )
            ),
            inspected_at TEXT NOT NULL,
            source_file_size_bytes INTEGER,
            source_file_modified_at TEXT,
            duration_seconds REAL,
            format_name TEXT,
            format_long_name TEXT,
            overall_bitrate INTEGER,
            stream_count INTEGER,
            video_stream_count INTEGER,
            audio_stream_count INTEGER,
            subtitle_stream_count INTEGER,
            width INTEGER,
            height INTEGER,
            display_aspect_ratio TEXT,
            pixel_aspect_ratio TEXT,
            frame_rate_numerator INTEGER,
            frame_rate_denominator INTEGER,
            average_frame_rate_numerator INTEGER,
            average_frame_rate_denominator INTEGER,
            video_codec TEXT,
            video_codec_profile TEXT,
            pixel_format TEXT,
            video_bitrate INTEGER,
            audio_codec TEXT,
            audio_sample_rate INTEGER,
            audio_channels INTEGER,
            audio_channel_layout TEXT,
            audio_bitrate INTEGER,
            rotation_degrees INTEGER,
            metadata_json TEXT NOT NULL,
            ffprobe_version TEXT,
            ffprobe_path TEXT,
            ffmpeg_version TEXT,
            ffmpeg_path TEXT,
            thumbnail_relative_path TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_inspections_video_asset_id ON video_inspections(video_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_inspections_status ON video_inspections(inspection_status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_inspections_inspected_at ON video_inspections(inspected_at)"
    )


def migration_3(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS prepared_audio_assets (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            source_inspection_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'not_prepared',
                    'queued',
                    'extracting',
                    'completed',
                    'failed',
                    'file_missing',
                    'no_audio_stream',
                    'tool_unavailable',
                    'stale'
                )
            ),
            relative_cache_path TEXT,
            metadata_relative_path TEXT,
            format_name TEXT,
            codec_name TEXT,
            sample_rate_hz INTEGER,
            channels INTEGER,
            channel_layout TEXT,
            bit_depth INTEGER,
            duration_seconds REAL,
            file_size_bytes INTEGER,
            source_file_size_bytes INTEGER,
            source_file_modified_at TEXT,
            selected_stream_index INTEGER,
            selected_stream_codec_name TEXT,
            selected_stream_channels INTEGER,
            selected_stream_channel_layout TEXT,
            selected_stream_sample_rate_hz INTEGER,
            selected_stream_language TEXT,
            selected_stream_is_default INTEGER,
            extraction_started_at TEXT,
            extraction_completed_at TEXT,
            ffmpeg_version TEXT,
            cache_version TEXT NOT NULL,
            normalization_sample_rate_hz INTEGER NOT NULL,
            normalization_channels INTEGER NOT NULL,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (source_inspection_id) REFERENCES video_inspections(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_prepared_audio_assets_video_asset_id ON prepared_audio_assets(video_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_prepared_audio_assets_source_inspection_id ON prepared_audio_assets(source_inspection_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_prepared_audio_assets_status ON prepared_audio_assets(status)"
    )


def migration_4(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transcriptions (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            prepared_audio_asset_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'not_transcribed',
                    'queued',
                    'loading_model',
                    'transcribing',
                    'completed',
                    'failed',
                    'cancelled',
                    'file_missing',
                    'audio_not_prepared',
                    'audio_stale',
                    'model_unavailable',
                    'backend_unavailable',
                    'stale'
                )
            ),
            engine TEXT NOT NULL,
            model_name TEXT NOT NULL,
            device TEXT NOT NULL,
            compute_type TEXT NOT NULL,
            requested_language TEXT,
            detected_language TEXT,
            language_probability REAL,
            full_text TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            processing_time_seconds REAL NOT NULL,
            real_time_factor REAL NOT NULL,
            segment_count INTEGER NOT NULL,
            word_timestamps_enabled INTEGER NOT NULL,
            vad_enabled INTEGER NOT NULL,
            source_audio_size_bytes INTEGER,
            source_audio_modified_at TEXT,
            source_audio_fingerprint TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            engine_version TEXT,
            model_version TEXT,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (prepared_audio_asset_id) REFERENCES prepared_audio_assets(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transcription_segments (
            id TEXT PRIMARY KEY,
            transcription_id TEXT NOT NULL,
            segment_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            text TEXT NOT NULL,
            confidence REAL,
            no_speech_probability REAL,
            temperature REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_transcriptions_video_asset_id ON transcriptions(video_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_transcriptions_prepared_audio_asset_id ON transcriptions(prepared_audio_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_transcription_segments_transcription_id ON transcription_segments(transcription_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_transcription_segments_segment_index ON transcription_segments(transcription_id, segment_index)"
    )


def migration_5(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS acoustic_analyses (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            prepared_audio_asset_id TEXT NOT NULL,
            transcription_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'not_analyzed',
                    'queued',
                    'reading_audio',
                    'analyzing_frames',
                    'combining_transcription',
                    'detecting_pauses_events',
                    'saving_results',
                    'completed',
                    'failed',
                    'cancelled',
                    'file_missing',
                    'audio_not_prepared',
                    'audio_stale',
                    'stale'
                )
            ),
            analyzer_version TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            source_audio_fingerprint TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            speech_duration_seconds REAL NOT NULL,
            silence_duration_seconds REAL NOT NULL,
            speech_ratio REAL NOT NULL,
            silence_ratio REAL NOT NULL,
            words_per_minute REAL,
            voiced_words_per_minute REAL,
            average_energy REAL NOT NULL,
            peak_energy REAL NOT NULL,
            dynamic_range REAL NOT NULL,
            pause_count INTEGER NOT NULL,
            average_pause_seconds REAL,
            longest_pause_seconds REAL,
            short_pause_count INTEGER NOT NULL,
            medium_pause_count INTEGER NOT NULL,
            long_pause_count INTEGER NOT NULL,
            low_activity_segment_count INTEGER NOT NULL,
            abrupt_change_count INTEGER NOT NULL,
            event_candidate_count INTEGER NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (prepared_audio_asset_id) REFERENCES prepared_audio_assets(id) ON DELETE SET NULL,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS acoustic_timeline_windows (
            id TEXT PRIMARY KEY,
            acoustic_analysis_id TEXT NOT NULL,
            window_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            speech_probability REAL NOT NULL,
            is_speech INTEGER NOT NULL,
            rms_energy REAL NOT NULL,
            peak_amplitude REAL NOT NULL,
            normalized_energy REAL NOT NULL,
            zero_crossing_rate REAL NOT NULL,
            speech_rate_estimate REAL,
            word_count INTEGER NOT NULL,
            pause_duration_seconds REAL NOT NULL,
            activity_label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (acoustic_analysis_id) REFERENCES acoustic_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS acoustic_events (
            id TEXT PRIMARY KEY,
            acoustic_analysis_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            event_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (acoustic_analysis_id) REFERENCES acoustic_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_analyses_video_asset_id ON acoustic_analyses(video_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_analyses_prepared_audio_asset_id ON acoustic_analyses(prepared_audio_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_analyses_status ON acoustic_analyses(status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_timeline_windows_analysis_id ON acoustic_timeline_windows(acoustic_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_timeline_windows_window_index ON acoustic_timeline_windows(acoustic_analysis_id, window_index)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_events_analysis_id ON acoustic_events(acoustic_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_acoustic_events_event_index ON acoustic_events(acoustic_analysis_id, event_index)"
    )


def migration_6(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS visual_analyses (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            source_inspection_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'not_analyzed',
                    'queued',
                    'preparing_video',
                    'sampling_frames',
                    'detecting_cuts',
                    'grouping_scenes',
                    'generating_keyframes',
                    'calculating_metrics',
                    'saving_results',
                    'completed',
                    'failed',
                    'cancelled',
                    'file_missing',
                    'inspection_missing',
                    'stale',
                    'tool_unavailable'
                )
            ),
            analyzer_version TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            source_file_size_bytes INTEGER,
            source_file_modified_at TEXT,
            duration_seconds REAL,
            sampled_frame_count INTEGER NOT NULL,
            detected_cut_count INTEGER NOT NULL,
            detected_scene_count INTEGER NOT NULL,
            keyframe_count INTEGER NOT NULL,
            static_segment_count INTEGER NOT NULL,
            black_frame_event_count INTEGER NOT NULL,
            freeze_event_count INTEGER NOT NULL,
            average_brightness REAL,
            brightness_variation REAL,
            average_contrast REAL,
            average_motion REAL,
            peak_motion REAL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (source_inspection_id) REFERENCES video_inspections(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS visual_timeline_windows (
            id TEXT PRIMARY KEY,
            visual_analysis_id TEXT NOT NULL,
            window_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            sampled_frame_count INTEGER NOT NULL,
            brightness REAL NOT NULL,
            contrast REAL NOT NULL,
            saturation REAL NOT NULL,
            motion_score REAL NOT NULL,
            color_change_score REAL NOT NULL,
            is_static INTEGER NOT NULL,
            is_black INTEGER NOT NULL,
            is_possible_freeze INTEGER NOT NULL,
            activity_label TEXT NOT NULL CHECK (
                activity_label IN (
                    'static',
                    'low_motion',
                    'moderate_motion',
                    'high_motion',
                    'dark',
                    'normal_exposure',
                    'bright',
                    'possible_black_frame',
                    'possible_freeze',
                    'transition_candidate',
                    'unknown'
                )
            ),
            created_at TEXT NOT NULL,
            FOREIGN KEY (visual_analysis_id) REFERENCES visual_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS visual_scenes (
            id TEXT PRIMARY KEY,
            visual_analysis_id TEXT NOT NULL,
            scene_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            representative_keyframe_path TEXT,
            cut_in_score REAL NOT NULL,
            average_motion REAL NOT NULL,
            average_brightness REAL NOT NULL,
            average_contrast REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (visual_analysis_id) REFERENCES visual_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS visual_events (
            id TEXT PRIMARY KEY,
            visual_analysis_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type IN (
                    'hard_cut',
                    'gradual_transition',
                    'flash_candidate',
                    'black_frame_candidate',
                    'freeze_candidate',
                    'abrupt_motion_change',
                    'abrupt_brightness_change'
                )
            ),
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (visual_analysis_id) REFERENCES visual_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_analyses_video_asset_id ON visual_analyses(video_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_analyses_source_inspection_id ON visual_analyses(source_inspection_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_analyses_status ON visual_analyses(status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_timeline_windows_analysis_id ON visual_timeline_windows(visual_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_timeline_windows_window_index ON visual_timeline_windows(visual_analysis_id, window_index)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_scenes_analysis_id ON visual_scenes(visual_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_scenes_scene_index ON visual_scenes(visual_analysis_id, scene_index)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_events_analysis_id ON visual_events(visual_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_visual_events_event_index ON visual_events(visual_analysis_id, event_index)"
    )


def migration_7(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS multimodal_analyses (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            transcription_id TEXT,
            acoustic_analysis_id TEXT,
            visual_analysis_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'not_analyzed',
                    'queued',
                    'loading_sources',
                    'aligning_timelines',
                    'normalizing_signals',
                    'detecting_changes',
                    'generating_candidates',
                    'fusing_candidates',
                    'saving_results',
                    'completed',
                    'failed',
                    'cancelled',
                    'stale'
                )
            ),
            analyzer_version TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            window_size_seconds REAL NOT NULL,
            window_count INTEGER NOT NULL,
            candidate_count INTEGER NOT NULL,
            high_activity_candidate_count INTEGER NOT NULL,
            transition_candidate_count INTEGER NOT NULL,
            silence_candidate_count INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE SET NULL,
            FOREIGN KEY (acoustic_analysis_id) REFERENCES acoustic_analyses(id) ON DELETE SET NULL,
            FOREIGN KEY (visual_analysis_id) REFERENCES visual_analyses(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS multimodal_timeline_windows (
            id TEXT PRIMARY KEY,
            multimodal_analysis_id TEXT NOT NULL,
            window_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            transcript_text TEXT NOT NULL,
            word_count INTEGER NOT NULL,
            speech_ratio REAL NOT NULL,
            silence_ratio REAL NOT NULL,
            speech_rate REAL,
            acoustic_energy REAL NOT NULL,
            acoustic_change REAL NOT NULL,
            visual_motion REAL NOT NULL,
            visual_change REAL NOT NULL,
            brightness REAL NOT NULL,
            cut_count INTEGER NOT NULL,
            scene_index INTEGER,
            acoustic_event_count INTEGER NOT NULL,
            visual_event_count INTEGER NOT NULL,
            combined_activity_score REAL NOT NULL,
            transition_score REAL NOT NULL,
            novelty_score REAL NOT NULL,
            confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (multimodal_analysis_id) REFERENCES multimodal_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS multimodal_moment_candidates (
            id TEXT PRIMARY KEY,
            multimodal_analysis_id TEXT NOT NULL,
            candidate_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            candidate_type TEXT NOT NULL CHECK (
                candidate_type IN (
                    'high_combined_activity',
                    'abrupt_multimodal_change',
                    'speech_energy_peak',
                    'visual_transition_with_speech',
                    'long_silence_or_pause',
                    'low_activity_segment',
                    'acoustic_event_with_visual_change',
                    'scene_opening',
                    'scene_closing',
                    'possible_hook_candidate',
                    'possible_reaction_candidate',
                    'unknown_candidate'
                )
            ),
            score REAL NOT NULL,
            confidence REAL NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            source_window_start REAL,
            source_window_end REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (multimodal_analysis_id) REFERENCES multimodal_analyses(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_analyses_video_asset_id ON multimodal_analyses(video_asset_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_analyses_transcription_id ON multimodal_analyses(transcription_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_analyses_acoustic_analysis_id ON multimodal_analyses(acoustic_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_analyses_visual_analysis_id ON multimodal_analyses(visual_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_analyses_status ON multimodal_analyses(status)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_timeline_windows_analysis_id ON multimodal_timeline_windows(multimodal_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_timeline_windows_window_index ON multimodal_timeline_windows(multimodal_analysis_id, window_index)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_moment_candidates_analysis_id ON multimodal_moment_candidates(multimodal_analysis_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_moment_candidates_candidate_index ON multimodal_moment_candidates(multimodal_analysis_id, candidate_index)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_multimodal_moment_candidates_type ON multimodal_moment_candidates(candidate_type)"
    )


def migration_8(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_ranking_runs (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL UNIQUE,
            multimodal_analysis_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'not_ranked',
                    'queued',
                    'scoring',
                    'adjusting_borders',
                    'resolving_overlaps',
                    'applying_diversity',
                    'migrating_feedback',
                    'saving_results',
                    'completed',
                    'failed',
                    'cancelled',
                    'stale'
                )
            ),
            ranker_version TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            candidate_count INTEGER NOT NULL,
            ranked_candidate_count INTEGER NOT NULL,
            selected_count INTEGER NOT NULL,
            rejected_count INTEGER NOT NULL,
            review_count INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (multimodal_analysis_id) REFERENCES multimodal_analyses(id) ON DELETE RESTRICT,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ranked_clip_candidates (
            id TEXT PRIMARY KEY,
            ranking_run_id TEXT NOT NULL,
            multimodal_candidate_id TEXT NOT NULL,
            rank_position INTEGER NOT NULL,
            original_start_seconds REAL NOT NULL,
            original_end_seconds REAL NOT NULL,
            adjusted_start_seconds REAL NOT NULL,
            adjusted_end_seconds REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            candidate_type TEXT NOT NULL,
            source_score REAL NOT NULL,
            source_confidence REAL NOT NULL,
            rank_score REAL NOT NULL,
            quality_score REAL NOT NULL,
            diversity_score REAL NOT NULL,
            overlap_penalty REAL NOT NULL,
            duration_score REAL NOT NULL,
            opening_score REAL NOT NULL,
            closing_score REAL NOT NULL,
            speech_score REAL NOT NULL,
            visual_score REAL NOT NULL,
            acoustic_score REAL NOT NULL,
            transition_score REAL NOT NULL,
            novelty_score REAL NOT NULL,
            evidence_strength_score REAL NOT NULL,
            review_status TEXT NOT NULL CHECK (
                review_status IN (
                    'unreviewed',
                    'shortlisted',
                    'approved',
                    'rejected',
                    'needs_review',
                    'duplicate',
                    'invalid',
                    'exported'
                )
            ),
            user_rating INTEGER,
            user_note TEXT,
            explanation_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (ranking_run_id) REFERENCES clip_ranking_runs(id) ON DELETE CASCADE,
            UNIQUE (ranking_run_id, multimodal_candidate_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_review_events (
            id TEXT PRIMARY KEY,
            ranked_clip_candidate_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            action TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            previous_start_seconds REAL,
            previous_end_seconds REAL,
            new_start_seconds REAL,
            new_end_seconds REAL,
            rating INTEGER,
            note TEXT,
            tags_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ranked_clip_candidate_id) REFERENCES ranked_clip_candidates(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_collections (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL CHECK (status IN ('active', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_collection_items (
            id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            ranked_clip_candidate_id TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            custom_title TEXT,
            custom_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (collection_id) REFERENCES clip_collections(id) ON DELETE CASCADE,
            FOREIGN KEY (ranked_clip_candidate_id) REFERENCES ranked_clip_candidates(id) ON DELETE CASCADE,
            UNIQUE (collection_id, ranked_clip_candidate_id)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_ranking_runs_video_asset_id ON clip_ranking_runs(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_ranking_runs_multimodal_analysis_id ON clip_ranking_runs(multimodal_analysis_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_ranking_runs_creator_id ON clip_ranking_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_ranking_runs_project_id ON clip_ranking_runs(project_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_ranking_runs_status ON clip_ranking_runs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_ranked_clip_candidates_run_id ON ranked_clip_candidates(ranking_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_ranked_clip_candidates_run_position ON ranked_clip_candidates(ranking_run_id, rank_position)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_ranked_clip_candidates_multimodal_candidate_id ON ranked_clip_candidates(multimodal_candidate_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_ranked_clip_candidates_review_status ON ranked_clip_candidates(review_status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_review_events_candidate_id ON clip_review_events(ranked_clip_candidate_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_review_events_event_index ON clip_review_events(ranked_clip_candidate_id, event_index)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_collections_video_asset_id ON clip_collections(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_collection_items_collection_id ON clip_collection_items(collection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_collection_items_candidate_id ON clip_collection_items(ranked_clip_candidate_id)")


def migration_9(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_dataset_snapshots (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            project_id TEXT,
            name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'building',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'stale',
                    'archived'
                )
            ),
            dataset_version TEXT NOT NULL,
            feature_schema_version TEXT NOT NULL,
            label_schema_version TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            example_count INTEGER NOT NULL,
            positive_count INTEGER NOT NULL,
            negative_count INTEGER NOT NULL,
            neutral_count INTEGER NOT NULL,
            excluded_count INTEGER NOT NULL,
            conflict_count INTEGER NOT NULL,
            train_count INTEGER NOT NULL,
            validation_count INTEGER NOT NULL,
            test_count INTEGER NOT NULL,
            readiness_status TEXT NOT NULL CHECK (
                readiness_status IN (
                    'not_ready',
                    'collecting_feedback',
                    'limited',
                    'ready_for_baseline',
                    'ready_for_evaluation',
                    'ready_for_personalized_training',
                    'blocked_by_quality',
                    'blocked_by_conflicts'
                )
            ),
            readiness_score REAL NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_dataset_examples (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            video_asset_id TEXT NOT NULL,
            ranking_run_id TEXT,
            ranked_clip_candidate_id TEXT,
            multimodal_candidate_id TEXT,
            group_key TEXT NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            label TEXT NOT NULL CHECK (
                label IN ('positive', 'negative', 'neutral_or_uncertain', 'excluded')
            ),
            label_source_json TEXT NOT NULL,
            label_confidence REAL NOT NULL,
            human_review_status TEXT,
            human_rating INTEGER,
            human_tags_json TEXT NOT NULL,
            feature_vector_json TEXT NOT NULL,
            feature_schema_version TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL,
            exclusion_reason TEXT,
            split_name TEXT NOT NULL CHECK (split_name IN ('train', 'validation', 'test', 'excluded')),
            sample_weight REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES creator_dataset_snapshots(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE RESTRICT,
            FOREIGN KEY (ranking_run_id) REFERENCES clip_ranking_runs(id) ON DELETE SET NULL,
            FOREIGN KEY (ranked_clip_candidate_id) REFERENCES ranked_clip_candidates(id) ON DELETE SET NULL,
            FOREIGN KEY (multimodal_candidate_id) REFERENCES multimodal_moment_candidates(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_dataset_conflicts (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            candidate_a_id TEXT,
            candidate_b_id TEXT,
            description TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            resolution_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (snapshot_id) REFERENCES creator_dataset_snapshots(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_dataset_quality_reports (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL UNIQUE,
            report_version TEXT NOT NULL,
            duplicate_ratio REAL NOT NULL,
            overlap_ratio REAL NOT NULL,
            missing_feature_ratio REAL NOT NULL,
            class_balance_score REAL NOT NULL,
            creator_coverage_score REAL NOT NULL,
            temporal_coverage_score REAL NOT NULL,
            source_diversity_score REAL NOT NULL,
            label_consistency_score REAL NOT NULL,
            leakage_risk_score REAL NOT NULL,
            readiness_score REAL NOT NULL,
            readiness_status TEXT NOT NULL CHECK (
                readiness_status IN (
                    'not_ready',
                    'collecting_feedback',
                    'limited',
                    'ready_for_baseline',
                    'ready_for_evaluation',
                    'ready_for_personalized_training',
                    'blocked_by_quality',
                    'blocked_by_conflicts'
                )
            ),
            recommendations_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES creator_dataset_snapshots(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_feature_schemas (
            id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            feature_names_json TEXT NOT NULL,
            feature_definitions_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_snapshots_creator_id ON creator_dataset_snapshots(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_snapshots_project_id ON creator_dataset_snapshots(project_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_snapshots_status ON creator_dataset_snapshots(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_snapshots_readiness_status ON creator_dataset_snapshots(readiness_status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_examples_snapshot_id ON creator_dataset_examples(snapshot_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_examples_creator_id ON creator_dataset_examples(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_examples_video_asset_id ON creator_dataset_examples(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_examples_group_key ON creator_dataset_examples(group_key)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_examples_label ON creator_dataset_examples(label)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_examples_split_name ON creator_dataset_examples(split_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_conflicts_snapshot_id ON creator_dataset_conflicts(snapshot_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_conflicts_creator_id ON creator_dataset_conflicts(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_conflicts_type ON creator_dataset_conflicts(conflict_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_dataset_quality_reports_snapshot_id ON creator_dataset_quality_reports(snapshot_id)")
    connection.execute(
        """
        INSERT OR IGNORE INTO creator_feature_schemas (
            id, schema_version, name, description, feature_names_json, feature_definitions_json, created_at
        ) VALUES (
            'creator-feature-schema-1',
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            CREATOR_FEATURE_SCHEMA_VERSION,
            CREATOR_FEATURE_SCHEMA_NAME,
            CREATOR_FEATURE_SCHEMA_DESCRIPTION,
            json.dumps(list(CREATOR_FEATURE_NAMES), ensure_ascii=False, sort_keys=True),
            json.dumps(CREATOR_FEATURE_DEFINITIONS, ensure_ascii=False, sort_keys=True, default=str),
            _utc_now(),
        ),
    )


def migration_10(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS personalization_training_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            project_id TEXT,
            snapshot_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'queued',
                    'validating_dataset',
                    'preparing_features',
                    'training',
                    'evaluating',
                    'saving_artifact',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'cancelled',
                    'blocked'
                )
            ),
            model_family TEXT NOT NULL,
            model_version TEXT NOT NULL,
            trainer_version TEXT NOT NULL,
            feature_schema_version TEXT NOT NULL,
            label_schema_version TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            train_count INTEGER NOT NULL,
            validation_count INTEGER NOT NULL,
            test_count INTEGER NOT NULL,
            positive_count INTEGER NOT NULL,
            negative_count INTEGER NOT NULL,
            excluded_count INTEGER NOT NULL,
            random_seed INTEGER NOT NULL,
            decision_threshold REAL NOT NULL,
            artifact_path TEXT,
            artifact_fingerprint TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (snapshot_id) REFERENCES creator_dataset_snapshots(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS personalization_model_metrics (
            id TEXT PRIMARY KEY,
            training_run_id TEXT NOT NULL,
            split_name TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            support INTEGER,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (training_run_id) REFERENCES personalization_training_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS personalization_model_predictions (
            id TEXT PRIMARY KEY,
            training_run_id TEXT NOT NULL,
            dataset_example_id TEXT NOT NULL,
            split_name TEXT NOT NULL,
            true_label TEXT,
            predicted_label TEXT NOT NULL,
            positive_score REAL NOT NULL,
            decision_threshold REAL NOT NULL,
            is_correct INTEGER,
            explanation_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (training_run_id) REFERENCES personalization_training_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS personalization_model_registry (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            project_id TEXT,
            training_run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'candidate',
                    'active',
                    'inactive',
                    'retired',
                    'invalid',
                    'artifact_missing',
                    'incompatible'
                )
            ),
            is_active INTEGER NOT NULL,
            activated_at TEXT,
            retired_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (training_run_id) REFERENCES personalization_training_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS personalization_model_comparisons (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            baseline_run_id TEXT NOT NULL,
            candidate_run_id TEXT NOT NULL,
            comparison_status TEXT NOT NULL,
            primary_metric TEXT NOT NULL,
            baseline_value REAL,
            candidate_value REAL,
            difference REAL,
            warnings_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_training_runs_creator_id ON personalization_training_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_training_runs_snapshot_id ON personalization_training_runs(snapshot_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_training_runs_status ON personalization_training_runs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_metrics_run_id ON personalization_model_metrics(training_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_metrics_split ON personalization_model_metrics(training_run_id, split_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_predictions_run_id ON personalization_model_predictions(training_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_predictions_split ON personalization_model_predictions(training_run_id, split_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_registry_creator_id ON personalization_model_registry(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_registry_active ON personalization_model_registry(creator_id, project_id, is_active)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_personalization_model_comparisons_creator_id ON personalization_model_comparisons(creator_id)")


def migration_11(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS operational_evaluation_runs (
            id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            creator_id TEXT,
            project_id TEXT,
            video_asset_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'queued',
                    'preparing_scenario',
                    'running',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'cancelled',
                    'blocked'
                )
            ),
            scenario_version TEXT NOT NULL,
            evaluator_version TEXT NOT NULL,
            configuration_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            total_duration_seconds REAL,
            stage_count INTEGER NOT NULL,
            completed_stage_count INTEGER NOT NULL,
            failed_stage_count INTEGER NOT NULL,
            warning_count INTEGER NOT NULL,
            assertion_pass_count INTEGER NOT NULL,
            assertion_fail_count INTEGER NOT NULL,
            cache_hit_count INTEGER NOT NULL,
            cache_miss_count INTEGER NOT NULL,
            final_result TEXT NOT NULL CHECK (
                final_result IN (
                    'passed',
                    'passed_with_warnings',
                    'failed',
                    'blocked',
                    'cancelled',
                    'inconclusive'
                )
            ),
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE SET NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS operational_evaluation_stages (
            id TEXT PRIMARY KEY,
            evaluation_run_id TEXT NOT NULL,
            stage_index INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'pending',
                    'running',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'skipped',
                    'cached',
                    'cancelled',
                    'blocked'
                )
            ),
            started_at TEXT,
            completed_at TEXT,
            duration_seconds REAL,
            input_summary_json TEXT NOT NULL,
            output_summary_json TEXT NOT NULL,
            cache_status TEXT NOT NULL,
            retry_count INTEGER NOT NULL,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evaluation_run_id) REFERENCES operational_evaluation_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS operational_evaluation_metrics (
            id TEXT PRIMARY KEY,
            evaluation_run_id TEXT NOT NULL,
            stage_name TEXT,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_unit TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evaluation_run_id) REFERENCES operational_evaluation_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS operational_evaluation_assertions (
            id TEXT PRIMARY KEY,
            evaluation_run_id TEXT NOT NULL,
            stage_name TEXT,
            assertion_name TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_json TEXT NOT NULL,
            actual_json TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evaluation_run_id) REFERENCES operational_evaluation_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS operational_evaluation_artifacts (
            id TEXT PRIMARY KEY,
            evaluation_run_id TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            managed_path TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            size_bytes INTEGER,
            exists_at_completion INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evaluation_run_id) REFERENCES operational_evaluation_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_runs_scenario_id ON operational_evaluation_runs(scenario_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_runs_creator_id ON operational_evaluation_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_runs_status ON operational_evaluation_runs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_stages_run_id ON operational_evaluation_stages(evaluation_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_stages_stage_name ON operational_evaluation_stages(evaluation_run_id, stage_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_metrics_run_id ON operational_evaluation_metrics(evaluation_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_assertions_run_id ON operational_evaluation_assertions(evaluation_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_operational_evaluation_artifacts_run_id ON operational_evaluation_artifacts(evaluation_run_id)")


def migration_12(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_jobs (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL,
            ranked_clip_candidate_id TEXT,
            collection_id TEXT,
            status TEXT NOT NULL CHECK (
                status IN (
                    'queued',
                    'validating',
                    'preparing',
                    'rendering',
                    'verifying',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'cancelled',
                    'interrupted',
                    'stale',
                    'source_missing',
                    'invalid_bounds',
                    'output_exists'
                )
            ),
            render_profile TEXT NOT NULL,
            source_path_snapshot TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            output_path TEXT NOT NULL,
            output_container TEXT NOT NULL,
            video_codec TEXT NOT NULL,
            audio_codec TEXT NOT NULL,
            width INTEGER,
            height INTEGER,
            frame_rate REAL,
            audio_sample_rate INTEGER,
            configuration_fingerprint TEXT NOT NULL,
            renderer_version TEXT NOT NULL,
            progress_percent REAL NOT NULL DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            cancelled_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_artifacts (
            id TEXT PRIMARY KEY,
            render_job_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            managed_path TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            size_bytes INTEGER,
            duration_seconds REAL,
            video_codec TEXT,
            audio_codec TEXT,
            width INTEGER,
            height INTEGER,
            frame_rate REAL,
            audio_sample_rate INTEGER,
            verified INTEGER NOT NULL DEFAULT 0,
            verification_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(render_job_id, artifact_type),
            FOREIGN KEY (render_job_id) REFERENCES clip_render_jobs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_events (
            id TEXT PRIMARY KEY,
            render_job_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            progress_percent REAL NOT NULL,
            message TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (render_job_id) REFERENCES clip_render_jobs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_batches (
            id TEXT PRIMARY KEY,
            collection_id TEXT,
            video_asset_id TEXT,
            name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'queued',
                    'running',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'cancelled',
                    'interrupted'
                )
            ),
            job_count INTEGER NOT NULL DEFAULT 0,
            completed_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            cancelled_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_batch_items (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            render_job_id TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(batch_id, render_job_id),
            FOREIGN KEY (batch_id) REFERENCES clip_render_batches(id) ON DELETE CASCADE,
            FOREIGN KEY (render_job_id) REFERENCES clip_render_jobs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_jobs_video_asset_id ON clip_render_jobs(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_jobs_candidate_id ON clip_render_jobs(ranked_clip_candidate_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_jobs_collection_id ON clip_render_jobs(collection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_jobs_status ON clip_render_jobs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_artifacts_render_job_id ON clip_render_artifacts(render_job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_events_render_job_id ON clip_render_events(render_job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_events_job_index ON clip_render_events(render_job_id, event_index)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_batches_collection_id ON clip_render_batches(collection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_batches_video_asset_id ON clip_render_batches(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_batches_status ON clip_render_batches(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_batch_items_batch_id ON clip_render_batch_items(batch_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_batch_items_job_id ON clip_render_batch_items(render_job_id)")


def migration_13(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subtitle_tracks (
            id TEXT PRIMARY KEY,
            video_asset_id TEXT NOT NULL,
            transcription_id TEXT NOT NULL,
            ranked_clip_candidate_id TEXT,
            render_job_id TEXT,
            language TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'generating',
                    'completed',
                    'completed_with_warnings',
                    'editing',
                    'locked',
                    'stale',
                    'failed',
                    'imported',
                    'archived'
                )
            ),
            source_type TEXT NOT NULL,
            track_version INTEGER NOT NULL DEFAULT 1,
            configuration_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            source_start_seconds REAL NOT NULL,
            source_end_seconds REAL NOT NULL,
            cue_count INTEGER NOT NULL DEFAULT 0,
            total_text_length INTEGER NOT NULL DEFAULT 0,
            is_default INTEGER NOT NULL DEFAULT 0,
            is_locked INTEGER NOT NULL DEFAULT 0,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE RESTRICT,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE RESTRICT,
            FOREIGN KEY (render_job_id) REFERENCES clip_render_jobs(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subtitle_cues (
            id TEXT PRIMARY KEY,
            subtitle_track_id TEXT NOT NULL,
            cue_index INTEGER NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            text TEXT NOT NULL,
            original_text TEXT NOT NULL,
            source_segment_ids_json TEXT NOT NULL,
            speaker_label TEXT,
            line_count INTEGER NOT NULL DEFAULT 1,
            character_count INTEGER NOT NULL DEFAULT 0,
            characters_per_second REAL NOT NULL DEFAULT 0,
            words_per_minute REAL NOT NULL DEFAULT 0,
            validation_status TEXT NOT NULL CHECK (validation_status IN ('valid', 'warning', 'invalid')),
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subtitle_track_id) REFERENCES subtitle_tracks(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subtitle_edit_events (
            id TEXT PRIMARY KEY,
            subtitle_track_id TEXT NOT NULL,
            subtitle_cue_id TEXT,
            event_index INTEGER NOT NULL,
            action TEXT NOT NULL,
            previous_json TEXT NOT NULL,
            new_json TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (subtitle_track_id) REFERENCES subtitle_tracks(id) ON DELETE CASCADE,
            FOREIGN KEY (subtitle_cue_id) REFERENCES subtitle_cues(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subtitle_exports (
            id TEXT PRIMARY KEY,
            subtitle_track_id TEXT NOT NULL,
            format TEXT NOT NULL,
            output_path TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            size_bytes INTEGER,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            verified_at TEXT,
            FOREIGN KEY (subtitle_track_id) REFERENCES subtitle_tracks(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_video_asset_id ON subtitle_tracks(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_transcription_id ON subtitle_tracks(transcription_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_candidate_id ON subtitle_tracks(ranked_clip_candidate_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_render_job_id ON subtitle_tracks(render_job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_tracks_status ON subtitle_tracks(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_cues_track_id ON subtitle_cues(subtitle_track_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_cues_track_order ON subtitle_cues(subtitle_track_id, cue_index)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_edit_events_track_id ON subtitle_edit_events(subtitle_track_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_edit_events_cue_id ON subtitle_edit_events(subtitle_cue_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_edit_events_track_order ON subtitle_edit_events(subtitle_track_id, event_index)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_exports_track_id ON subtitle_exports(subtitle_track_id)")


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="initial_schema"),
    Migration(version=2, name="video_inspections"),
    Migration(version=3, name="prepared_audio_assets"),
    Migration(version=4, name="transcriptions"),
    Migration(version=5, name="acoustic_analysis"),
    Migration(version=6, name="visual_analysis"),
    Migration(version=7, name="multimodal_analysis"),
    Migration(version=8, name="clip_ranking"),
    Migration(version=9, name="personalization_data"),
    Migration(version=10, name="personalization_models"),
    Migration(version=11, name="operational_evaluation"),
    Migration(version=12, name="clip_rendering"),
    Migration(version=13, name="subtitles"),
)


def _applied_migrations(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = connection.execute(
        "SELECT version, name, applied_at FROM schema_migrations ORDER BY version ASC"
    ).fetchall()
    return list(rows)


def _validate_applied_migrations(rows: list[sqlite3.Row]) -> None:
    versions = [int(row["version"]) for row in rows]
    if len(versions) != len(set(versions)):
        raise MigrationError("schema_migrations contiene versiones duplicadas.")
    if versions and versions != list(range(1, max(versions) + 1)):
        raise MigrationError("schema_migrations tiene huecos o un estado inconsistente.")
    known_versions = {migration.version for migration in MIGRATIONS}
    unknown = [version for version in versions if version not in known_versions]
    if unknown:
        raise MigrationError(
            f"schema_migrations contiene versiones desconocidas: {unknown}"
        )


def run_migrations(connection: sqlite3.Connection) -> None:
    """Aplica migraciones en orden y de forma idempotente."""

    ensure_schema_migrations_table(connection)
    rows = _applied_migrations(connection)
    _validate_applied_migrations(rows)

    applied_versions = {int(row["version"]) for row in rows}
    for migration in MIGRATIONS:
        if migration.version in applied_versions:
            continue
        try:
            with connection:
                if migration.version == 1:
                    migration_1(connection)
                elif migration.version == 2:
                    migration_2(connection)
                elif migration.version == 3:
                    migration_3(connection)
                elif migration.version == 4:
                    migration_4(connection)
                elif migration.version == 5:
                    migration_5(connection)
                elif migration.version == 6:
                    migration_6(connection)
                elif migration.version == 7:
                    migration_7(connection)
                elif migration.version == 8:
                    migration_8(connection)
                elif migration.version == 9:
                    migration_9(connection)
                elif migration.version == 10:
                    migration_10(connection)
                elif migration.version == 11:
                    migration_11(connection)
                elif migration.version == 12:
                    migration_12(connection)
                elif migration.version == 13:
                    migration_13(connection)
                else:  # pragma: no cover - no more migrations yet
                    migration.apply(connection)
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    """,
                    (migration.version, migration.name, _utc_now()),
                )
        except sqlite3.Error as exc:
            raise MigrationError(
                f"No se pudo aplicar la migracion {migration.version}: {migration.name}"
            ) from exc
