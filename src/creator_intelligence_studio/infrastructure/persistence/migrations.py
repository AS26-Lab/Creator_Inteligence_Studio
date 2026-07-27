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


def migration_14(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_deliveries (
            id TEXT PRIMARY KEY,
            render_job_id TEXT NOT NULL,
            subtitle_track_id TEXT,
            subtitle_track_version INTEGER,
            subtitle_track_fingerprint TEXT,
            subtitle_mode TEXT NOT NULL,
            subtitle_format TEXT,
            style_preset TEXT,
            style_json TEXT NOT NULL,
            source_export_path TEXT,
            source_export_fingerprint TEXT,
            expected_cue_count INTEGER NOT NULL DEFAULT 0,
            rendered_cue_count INTEGER NOT NULL DEFAULT 0,
            output_path TEXT,
            manifest_path TEXT,
            configuration_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'queued',
                    'preparing',
                    'rendering',
                    'verifying',
                    'completed',
                    'completed_with_warnings',
                    'failed',
                    'cancelled',
                    'interrupted',
                    'stale',
                    'output_exists',
                    'invalid_track',
                    'source_missing',
                    'bounds_mismatch'
                )
            ),
            progress_percent REAL NOT NULL DEFAULT 0,
            warning_code TEXT,
            warning_message TEXT,
            error_code TEXT,
            error_message TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            cancelled_at TEXT,
            UNIQUE(configuration_fingerprint),
            FOREIGN KEY (render_job_id) REFERENCES clip_render_jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (subtitle_track_id) REFERENCES subtitle_tracks(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clip_render_delivery_artifacts (
            id TEXT PRIMARY KEY,
            delivery_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            managed_path TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            size_bytes INTEGER,
            verified INTEGER NOT NULL DEFAULT 0,
            verification_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (delivery_id) REFERENCES clip_render_deliveries(id) ON DELETE CASCADE,
            UNIQUE(delivery_id, artifact_type)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_deliveries_render_job_id ON clip_render_deliveries(render_job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_deliveries_track_id ON clip_render_deliveries(subtitle_track_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_deliveries_status ON clip_render_deliveries(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_delivery_artifacts_delivery_id ON clip_render_delivery_artifacts(delivery_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_clip_render_delivery_artifacts_type ON clip_render_delivery_artifacts(delivery_id, artifact_type)")


def migration_15(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_platforms (
            id TEXT PRIMARY KEY,
            platform_key TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'archived', 'disabled')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_channels (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            platform_id TEXT NOT NULL,
            external_channel_id TEXT,
            channel_name TEXT NOT NULL,
            channel_url TEXT,
            timezone_name TEXT NOT NULL DEFAULT 'UTC',
            is_primary INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT,
            FOREIGN KEY (platform_id) REFERENCES analytics_platforms(id) ON DELETE RESTRICT,
            UNIQUE (creator_id, platform_id, channel_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_publications (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            channel_id TEXT,
            video_asset_id TEXT,
            external_publication_id TEXT,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL CHECK (
                content_type IN (
                    'longform_video',
                    'short_video',
                    'reel',
                    'tiktok',
                    'live_replay',
                    'community_post',
                    'other'
                )
            ),
            title TEXT NOT NULL,
            description TEXT,
            published_at TEXT NOT NULL,
            duration_seconds REAL,
            url TEXT,
            thumbnail_path TEXT,
            status TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK (source_type IN ('csv', 'xlsx', 'manual')),
            source_fingerprint TEXT NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT,
            FOREIGN KEY (channel_id) REFERENCES analytics_channels(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_metric_definitions (
            id TEXT PRIMARY KEY,
            metric_key TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            category TEXT NOT NULL CHECK (
                category IN ('discovery', 'attention', 'conversion', 'interaction', 'relation', 'context')
            ),
            unit TEXT NOT NULL,
            value_type TEXT NOT NULL CHECK (value_type IN ('numeric', 'text', 'category')),
            aggregation_type TEXT NOT NULL CHECK (aggregation_type IN ('latest', 'sum', 'avg', 'max', 'min', 'count')),
            higher_is_better INTEGER,
            description TEXT NOT NULL,
            aliases_json TEXT NOT NULL,
            applicability_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_imports (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            channel_id TEXT,
            platform TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            source_path TEXT,
            source_fingerprint TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK (source_type IN ('csv', 'xlsx', 'manual')),
            schema_version TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('queued', 'running', 'verifying', 'completed', 'completed_with_warnings', 'failed', 'cancelled', 'interrupted')
            ),
            total_rows INTEGER NOT NULL,
            accepted_rows INTEGER NOT NULL,
            rejected_rows INTEGER NOT NULL,
            warning_rows INTEGER NOT NULL,
            duplicate_rows INTEGER NOT NULL,
            source_sheet_name TEXT,
            timezone_name TEXT,
            delimiter TEXT,
            mapping_json TEXT NOT NULL,
            report_path TEXT,
            started_at TEXT,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE RESTRICT,
            FOREIGN KEY (channel_id) REFERENCES analytics_channels(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_import_rows (
            id TEXT PRIMARY KEY,
            import_id TEXT NOT NULL,
            row_number INTEGER NOT NULL,
            raw_json TEXT NOT NULL,
            normalized_json TEXT,
            status TEXT NOT NULL CHECK (status IN ('accepted', 'accepted_with_warnings', 'rejected', 'duplicate', 'skipped')),
            publication_id TEXT,
            warning_codes_json TEXT NOT NULL,
            error_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            FOREIGN KEY (import_id) REFERENCES analytics_imports(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            UNIQUE (import_id, row_number, row_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_metric_snapshots (
            id TEXT PRIMARY KEY,
            publication_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT NOT NULL,
            source_import_id TEXT NOT NULL,
            source_row_number INTEGER,
            is_derived INTEGER NOT NULL DEFAULT 0,
            quality_status TEXT NOT NULL CHECK (
                quality_status IN ('accepted', 'accepted_with_warnings', 'rejected', 'duplicate', 'skipped')
            ),
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE CASCADE,
            FOREIGN KEY (source_import_id) REFERENCES analytics_imports(id) ON DELETE RESTRICT,
            FOREIGN KEY (metric_key) REFERENCES analytics_metric_definitions(metric_key) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_field_mappings (
            id TEXT PRIMARY KEY,
            creator_id TEXT,
            platform TEXT NOT NULL,
            mapping_name TEXT NOT NULL,
            source_field TEXT NOT NULL,
            target_field TEXT NOT NULL,
            transformation TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            mapping_origin TEXT NOT NULL CHECK (mapping_origin IN ('auto', 'manual')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_channels_creator_id ON analytics_channels(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_channels_platform_id ON analytics_channels(platform_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_publications_creator_id ON analytics_publications(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_publications_channel_id ON analytics_publications(channel_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_publications_platform ON analytics_publications(platform)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_publications_video_asset_id ON analytics_publications(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_publications_published_at ON analytics_publications(published_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_metric_definitions_category ON analytics_metric_definitions(category)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_imports_creator_id ON analytics_imports(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_imports_channel_id ON analytics_imports(channel_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_imports_status ON analytics_imports(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_import_rows_import_id ON analytics_import_rows(import_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_import_rows_status ON analytics_import_rows(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_metric_snapshots_publication_id ON analytics_metric_snapshots(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_metric_snapshots_metric_key ON analytics_metric_snapshots(metric_key)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_metric_snapshots_snapshot_date ON analytics_metric_snapshots(snapshot_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_metric_snapshots_import_id ON analytics_metric_snapshots(source_import_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_field_mappings_creator_platform ON analytics_field_mappings(creator_id, platform)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_field_mappings_active ON analytics_field_mappings(is_active)")


def migration_16(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_cohort_definitions (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            date_from TEXT,
            date_to TEXT,
            duration_min_seconds REAL,
            duration_max_seconds REAL,
            topic TEXT,
            format TEXT,
            language TEXT,
            filters_json TEXT NOT NULL,
            is_system INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_analysis_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            run_type TEXT NOT NULL CHECK (run_type IN ('cohort_analysis', 'publication_comparison', 'weekly_report')),
            cohort_id TEXT,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'completed_with_warnings', 'failed', 'cancelled', 'interrupted')),
            configuration_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            publication_count INTEGER NOT NULL,
            metric_count INTEGER NOT NULL,
            warning_count INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (cohort_id) REFERENCES analytics_cohort_definitions(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_comparison_results (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            publication_id TEXT,
            cohort_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            observed_value REAL,
            cohort_count INTEGER NOT NULL,
            cohort_min REAL,
            cohort_max REAL,
            cohort_mean REAL,
            cohort_median REAL,
            percentile REAL,
            lower_quartile REAL,
            upper_quartile REAL,
            robust_z_score REAL,
            comparison_status TEXT NOT NULL CHECK (
                comparison_status IN ('comparable', 'insufficient_sample', 'incomparable', 'no_data', 'outlier_dominated')
            ),
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id) REFERENCES analytics_analysis_runs(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (cohort_id) REFERENCES analytics_cohort_definitions(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_findings (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            publication_id TEXT,
            cohort_id TEXT,
            finding_type TEXT NOT NULL CHECK (
                finding_type IN ('fact', 'comparison', 'anomaly', 'pattern', 'inference', 'hypothesis', 'data_quality_warning')
            ),
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('low', 'medium', 'high')),
            confidence_score REAL,
            sample_size INTEGER NOT NULL,
            contradiction_count INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'confirmed', 'rejected', 'needs_more_data', 'not_useful')),
            is_confirmed INTEGER NOT NULL DEFAULT 0,
            confirmed_at TEXT,
            rejected_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id) REFERENCES analytics_analysis_runs(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (cohort_id) REFERENCES analytics_cohort_definitions(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_report_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            report_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'completed_with_warnings', 'failed', 'cancelled', 'interrupted')),
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            configuration_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            finding_count INTEGER NOT NULL,
            warning_count INTEGER NOT NULL,
            output_json_path TEXT,
            output_txt_path TEXT,
            output_csv_path TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, report_type, source_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_report_items (
            id TEXT PRIMARY KEY,
            report_run_id TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            section TEXT NOT NULL,
            finding_id TEXT,
            item_type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (report_run_id) REFERENCES analytics_report_runs(id) ON DELETE CASCADE,
            FOREIGN KEY (finding_id) REFERENCES analytics_findings(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_cohort_definitions_creator_id ON analytics_cohort_definitions(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_cohort_definitions_active ON analytics_cohort_definitions(is_active)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_cohort_definitions_platform ON analytics_cohort_definitions(platform)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_analysis_runs_creator_id ON analytics_analysis_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_analysis_runs_cohort_id ON analytics_analysis_runs(cohort_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_analysis_runs_type ON analytics_analysis_runs(run_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_analysis_runs_status ON analytics_analysis_runs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_analysis_runs_fingerprint ON analytics_analysis_runs(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_comparison_results_run_id ON analytics_comparison_results(analysis_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_comparison_results_publication_id ON analytics_comparison_results(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_comparison_results_cohort_id ON analytics_comparison_results(cohort_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_comparison_results_metric_key ON analytics_comparison_results(metric_key)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_findings_creator_id ON analytics_findings(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_findings_run_id ON analytics_findings(analysis_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_findings_cohort_id ON analytics_findings(cohort_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_findings_publication_id ON analytics_findings(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_findings_type ON analytics_findings(finding_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_findings_status ON analytics_findings(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_report_runs_creator_id ON analytics_report_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_report_runs_type ON analytics_report_runs(report_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_report_runs_status ON analytics_report_runs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_report_runs_fingerprint ON analytics_report_runs(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_report_items_report_id ON analytics_report_items(report_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_report_items_finding_id ON analytics_report_items(finding_id)")


def migration_17(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_definitions (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            experiment_type TEXT NOT NULL CHECK (
                experiment_type IN (
                    'single_variable_test',
                    'before_after_observation',
                    'cohort_comparison',
                    'sequential_test',
                    'manual_observation'
                )
            ),
            platform TEXT,
            content_type TEXT,
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived', 'completed')),
            hypothesis TEXT NOT NULL,
            rationale TEXT NOT NULL,
            primary_metric_key TEXT NOT NULL,
            expected_direction TEXT NOT NULL,
            minimum_sample_size INTEGER NOT NULL,
            start_date TEXT,
            end_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_variables (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            variable_key TEXT NOT NULL,
            variable_type TEXT NOT NULL,
            description TEXT NOT NULL,
            control_value_json TEXT NOT NULL,
            treatment_value_json TEXT NOT NULL,
            allowed_values_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE CASCADE,
            UNIQUE (experiment_id, variable_key)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_guardrails (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            comparison_operator TEXT NOT NULL,
            threshold_value REAL,
            allowed_change REAL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE CASCADE,
            UNIQUE (experiment_id, metric_key)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_assignments (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            publication_id TEXT,
            planned_variant TEXT NOT NULL,
            actual_variant TEXT,
            assignment_status TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            executed_at TEXT,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            UNIQUE (experiment_id, publication_id, planned_variant)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_records (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT,
            recommendation_type TEXT NOT NULL CHECK (
                recommendation_type IN (
                    'content_structure',
                    'hook',
                    'duration',
                    'publication_timing',
                    'title_direction',
                    'thumbnail_direction',
                    'copy',
                    'caption',
                    'text_overlay',
                    'clip_selection',
                    'platform_adaptation',
                    'pacing',
                    'call_to_action',
                    'other'
                )
            ),
            platform TEXT,
            content_type TEXT,
            title TEXT NOT NULL,
            recommendation_text TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high')),
            confidence_score REAL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_decisions (
            id TEXT PRIMARY KEY,
            recommendation_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK (
                decision IN (
                    'accepted',
                    'accepted_with_changes',
                    'rejected',
                    'postponed',
                    'not_applicable',
                    'needs_more_data'
                )
            ),
            reason TEXT NOT NULL,
            modified_value_json TEXT,
            decided_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (recommendation_id) REFERENCES recommendation_records(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_records (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            recommendation_id TEXT,
            experiment_assignment_id TEXT,
            publication_id TEXT,
            execution_status TEXT NOT NULL CHECK (
                execution_status IN ('planned', 'used_as_recommended', 'used_with_changes', 'not_used', 'unknown')
            ),
            executed_value_json TEXT NOT NULL,
            deviation_from_recommendation_json TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (recommendation_id) REFERENCES recommendation_records(id) ON DELETE SET NULL,
            FOREIGN KEY (experiment_assignment_id) REFERENCES experiment_assignments(id) ON DELETE SET NULL,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_evaluations (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            evaluation_status TEXT NOT NULL CHECK (
                evaluation_status IN (
                    'queued',
                    'running',
                    'evaluating',
                    'completed',
                    'completed_with_warnings',
                    'interrupted',
                    'failed',
                    'cancelled'
                )
            ),
            sample_size INTEGER NOT NULL,
            control_count INTEGER NOT NULL,
            treatment_count INTEGER NOT NULL,
            primary_metric_key TEXT NOT NULL,
            control_result REAL,
            treatment_result REAL,
            absolute_difference REAL,
            relative_difference REAL,
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high')),
            uncertainty_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            evaluated_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_outcomes (
            id TEXT PRIMARY KEY,
            evaluation_id TEXT NOT NULL,
            publication_id TEXT NOT NULL,
            assignment_id TEXT,
            variant TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            observed_value REAL,
            comparable_window TEXT NOT NULL,
            quality_status TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES experiment_evaluations(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE CASCADE,
            FOREIGN KEY (assignment_id) REFERENCES experiment_assignments(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_records (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            learning_type TEXT NOT NULL CHECK (
                learning_type IN (
                    'observed_pattern',
                    'provisional_learning',
                    'confirmed_learning',
                    'rejected_learning',
                    'deprecated_learning',
                    'needs_more_data'
                )
            ),
            scope TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            statement TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            supporting_example_count INTEGER NOT NULL,
            contradicting_example_count INTEGER NOT NULL,
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high')),
            confidence_score REAL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'provisional', 'confirmed', 'rejected', 'deprecated', 'needs_more_data')),
            first_observed_at TEXT NOT NULL,
            last_reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_reviews (
            id TEXT PRIMARY KEY,
            learning_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK (
                decision IN ('confirm', 'reject', 'needs_more_data', 'deprecate', 'edit_statement')
            ),
            reason TEXT NOT NULL,
            reviewed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (learning_id) REFERENCES learning_records(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment_reports (
            id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            evaluation_id TEXT,
            source_fingerprint TEXT NOT NULL,
            configuration_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'completed_with_warnings', 'failed', 'cancelled', 'interrupted')),
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            output_json_path TEXT,
            output_txt_path TEXT,
            output_csv_path TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE CASCADE,
            FOREIGN KEY (evaluation_id) REFERENCES experiment_evaluations(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_definitions_creator_id ON experiment_definitions(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_definitions_status ON experiment_definitions(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_definitions_platform ON experiment_definitions(platform)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_variables_experiment_id ON experiment_variables(experiment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_guardrails_experiment_id ON experiment_guardrails(experiment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_assignments_experiment_id ON experiment_assignments(experiment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_assignments_publication_id ON experiment_assignments(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_records_creator_id ON recommendation_records(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_records_source_id ON recommendation_records(source_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_decisions_recommendation_id ON recommendation_decisions(recommendation_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_execution_records_creator_id ON execution_records(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_execution_records_recommendation_id ON execution_records(recommendation_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_execution_records_assignment_id ON execution_records(experiment_assignment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_execution_records_publication_id ON execution_records(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_evaluations_experiment_id ON experiment_evaluations(experiment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_evaluations_status ON experiment_evaluations(evaluation_status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_evaluations_fingerprint ON experiment_evaluations(uncertainty_json)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_outcomes_evaluation_id ON experiment_outcomes(evaluation_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_outcomes_publication_id ON experiment_outcomes(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_learning_records_creator_id ON learning_records(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_learning_records_status ON learning_records(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_learning_reviews_learning_id ON learning_reviews(learning_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_reports_experiment_id ON experiment_reports(experiment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_reports_status ON experiment_reports(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_experiment_reports_fingerprint ON experiment_reports(source_fingerprint)")


def migration_18(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_profiles (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'archived')),
            summary TEXT,
            primary_language TEXT,
            secondary_languages_json TEXT NOT NULL,
            default_tone TEXT,
            default_formality TEXT,
            objectives_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_traits (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            trait_type TEXT NOT NULL,
            trait_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT,
            value_json TEXT NOT NULL,
            scope TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            confidence_level TEXT NOT NULL,
            confidence_score REAL,
            status TEXT NOT NULL,
            first_observed_at TEXT,
            last_observed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, trait_key, scope, platform, content_type, topic)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_trait_evidence (
            id TEXT PRIMARY KEY,
            trait_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT,
            publication_id TEXT,
            video_asset_id TEXT,
            transcript_segment_id TEXT,
            start_seconds REAL,
            end_seconds REAL,
            quoted_text TEXT,
            evidence_type TEXT NOT NULL,
            supports_trait INTEGER NOT NULL,
            weight REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (trait_id) REFERENCES creator_traits(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_examples (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            example_type TEXT NOT NULL,
            category TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            title TEXT NOT NULL,
            text_content TEXT,
            source_type TEXT NOT NULL,
            source_id TEXT,
            publication_id TEXT,
            video_asset_id TEXT,
            start_seconds REAL,
            end_seconds REAL,
            representativeness REAL,
            approval_status TEXT NOT NULL,
            approval_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_vocabulary (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            term TEXT NOT NULL,
            normalized_term TEXT NOT NULL,
            vocabulary_type TEXT NOT NULL,
            meaning TEXT,
            usage_notes TEXT,
            platform TEXT,
            content_type TEXT,
            frequency_count INTEGER NOT NULL,
            confidence_level TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, normalized_term, vocabulary_type, platform, content_type)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_style_rules (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            rule_type TEXT NOT NULL,
            scope TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            statement TEXT NOT NULL,
            rationale TEXT,
            status TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            supporting_example_count INTEGER NOT NULL,
            contradicting_example_count INTEGER NOT NULL,
            first_observed_at TEXT,
            last_reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, rule_type, scope, platform, content_type, topic, statement)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_style_rule_reviews (
            id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            previous_statement TEXT,
            new_statement TEXT,
            reason TEXT NOT NULL,
            reviewed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (rule_id) REFERENCES creator_style_rules(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_limits (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            limit_type TEXT NOT NULL,
            category TEXT NOT NULL,
            statement TEXT NOT NULL,
            severity TEXT NOT NULL,
            scope TEXT NOT NULL,
            platform TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, limit_type, category, scope, platform, statement)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_profile_snapshots (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, profile_version),
            UNIQUE (creator_id, source_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_memory_feedback (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            corrected_value_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_profiles_creator_id ON creator_profiles(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_profiles_status ON creator_profiles(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_traits_creator_id ON creator_traits(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_traits_type ON creator_traits(trait_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_traits_scope ON creator_traits(scope)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_trait_evidence_trait_id ON creator_trait_evidence(trait_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_examples_creator_id ON creator_examples(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_examples_example_type ON creator_examples(example_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_vocabulary_creator_id ON creator_vocabulary(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_vocabulary_normalized_term ON creator_vocabulary(normalized_term)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_style_rules_creator_id ON creator_style_rules(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_style_rule_reviews_rule_id ON creator_style_rule_reviews(rule_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_limits_creator_id ON creator_limits(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_profile_snapshots_creator_id ON creator_profile_snapshots(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_profile_snapshots_fingerprint ON creator_profile_snapshots(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creator_memory_feedback_creator_id ON creator_memory_feedback(creator_id)")


def migration_19(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_corpora (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            language TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            status TEXT NOT NULL CHECK (status IN ('active', 'archived', 'draft')),
            source_count INTEGER NOT NULL,
            token_count INTEGER NOT NULL,
            duration_seconds REAL,
            source_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, source_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_corpus_sources (
            id TEXT PRIMARY KEY,
            corpus_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            video_asset_id TEXT,
            publication_id TEXT,
            transcription_id TEXT,
            segment_id TEXT,
            start_seconds REAL,
            end_seconds REAL,
            text_snapshot TEXT NOT NULL,
            language TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            include_status TEXT NOT NULL CHECK (include_status IN ('included', 'excluded', 'pending')),
            exclusion_reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (corpus_id) REFERENCES creator_language_corpora(id) ON DELETE CASCADE,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE SET NULL,
            FOREIGN KEY (segment_id) REFERENCES transcription_segments(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_corpora_creator_id ON creator_language_corpora(creator_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_corpora_fingerprint ON creator_language_corpora(source_fingerprint)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_corpus_sources_corpus_id ON creator_language_corpus_sources(corpus_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_corpus_sources_source_id ON creator_language_corpus_sources(source_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_corpus_sources_include_status ON creator_language_corpus_sources(include_status)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_analysis_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            corpus_id TEXT NOT NULL,
            analysis_version TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('queued', 'running', 'analyzing', 'building_profile', 'completed', 'completed_with_warnings', 'interrupted', 'failed', 'cancelled')
            ),
            configuration_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            token_count INTEGER NOT NULL,
            sentence_count INTEGER NOT NULL,
            warning_count INTEGER NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (corpus_id) REFERENCES creator_language_corpora(id) ON DELETE CASCADE,
            UNIQUE (creator_id, source_fingerprint, analysis_version)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_analysis_runs_creator_id ON creator_language_analysis_runs(creator_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_analysis_runs_corpus_id ON creator_language_analysis_runs(corpus_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_analysis_runs_fingerprint ON creator_language_analysis_runs(source_fingerprint)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_metrics (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            metric_group TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT NOT NULL,
            scope TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            sample_size INTEGER NOT NULL,
            confidence_level TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id) REFERENCES creator_language_analysis_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_metrics_run_id ON creator_language_metrics(analysis_run_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_metrics_metric_key ON creator_language_metrics(metric_key)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_patterns (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            scope TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            frequency_count INTEGER NOT NULL,
            supporting_example_count INTEGER NOT NULL,
            contradicting_example_count INTEGER NOT NULL,
            confidence_level TEXT NOT NULL,
            confidence_score REAL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id) REFERENCES creator_language_analysis_runs(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (analysis_run_id, pattern_key)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_patterns_creator_id ON creator_language_patterns(creator_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_patterns_run_id ON creator_language_patterns(analysis_run_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_patterns_type ON creator_language_patterns(pattern_type)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_pattern_evidence (
            id TEXT PRIMARY KEY,
            pattern_id TEXT NOT NULL,
            corpus_source_id TEXT NOT NULL,
            start_seconds REAL,
            end_seconds REAL,
            quoted_text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            supports_pattern INTEGER NOT NULL,
            weight REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (pattern_id) REFERENCES creator_language_patterns(id) ON DELETE CASCADE,
            FOREIGN KEY (corpus_source_id) REFERENCES creator_language_corpus_sources(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_pattern_evidence_pattern_id ON creator_language_pattern_evidence(pattern_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_pattern_evidence_source_id ON creator_language_pattern_evidence(corpus_source_id)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_narrative_profiles (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            analysis_run_id TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            status TEXT NOT NULL,
            summary TEXT NOT NULL,
            opening_profile_json TEXT NOT NULL,
            development_profile_json TEXT NOT NULL,
            explanation_profile_json TEXT NOT NULL,
            humor_profile_json TEXT NOT NULL,
            pacing_profile_json TEXT NOT NULL,
            closing_profile_json TEXT NOT NULL,
            platform_differences_json TEXT NOT NULL,
            content_type_differences_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (analysis_run_id) REFERENCES creator_language_analysis_runs(id) ON DELETE CASCADE,
            UNIQUE (creator_id, profile_version)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_narrative_profiles_creator_id ON creator_narrative_profiles(creator_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_narrative_profiles_run_id ON creator_narrative_profiles(analysis_run_id)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_candidates (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            analysis_run_id TEXT NOT NULL,
            candidate_type TEXT NOT NULL,
            target_memory_type TEXT NOT NULL,
            proposed_key TEXT NOT NULL,
            proposed_value_json TEXT NOT NULL,
            scope TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            evidence_json TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            status TEXT NOT NULL,
            review_reason TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (analysis_run_id) REFERENCES creator_language_analysis_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_candidates_creator_id ON creator_language_candidates(creator_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_candidates_run_id ON creator_language_candidates(analysis_run_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_candidates_status ON creator_language_candidates(status)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creator_language_profile_snapshots (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, profile_version),
            UNIQUE (creator_id, source_fingerprint)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_profile_snapshots_creator_id ON creator_language_profile_snapshots(creator_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_creator_language_profile_snapshots_fingerprint ON creator_language_profile_snapshots(source_fingerprint)"
    )


def migration_20(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_assets (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            asset_type TEXT NOT NULL CHECK (
                asset_type IN (
                    'title',
                    'thumbnail',
                    'title_thumbnail_pair',
                    'frame_candidate',
                    'creative_concept',
                    'creative_prompt',
                    'reference_image',
                    'designer_brief',
                    'thumbnail_review'
                )
            ),
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            topic TEXT,
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS title_versions (
            id TEXT PRIMARY KEY,
            packaging_asset_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            title_text TEXT NOT NULL,
            source_type TEXT NOT NULL,
            language TEXT NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            topic TEXT,
            is_published INTEGER NOT NULL DEFAULT 0,
            is_selected INTEGER NOT NULL DEFAULT 0,
            creator_approval_status TEXT NOT NULL,
            creator_feedback TEXT,
            source_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (packaging_asset_id) REFERENCES packaging_assets(id) ON DELETE CASCADE,
            UNIQUE (packaging_asset_id, version_number),
            UNIQUE (packaging_asset_id, source_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_versions (
            id TEXT PRIMARY KEY,
            packaging_asset_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            image_path TEXT,
            source_type TEXT NOT NULL,
            width INTEGER,
            height INTEGER,
            file_fingerprint TEXT,
            concept_id TEXT,
            is_published INTEGER NOT NULL DEFAULT 0,
            is_selected INTEGER NOT NULL DEFAULT 0,
            creator_approval_status TEXT NOT NULL,
            creator_feedback TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (packaging_asset_id) REFERENCES packaging_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (concept_id) REFERENCES creative_concepts(id) ON DELETE SET NULL,
            UNIQUE (packaging_asset_id, version_number),
            UNIQUE (packaging_asset_id, file_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_reference_assets (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            reference_type TEXT NOT NULL,
            image_path TEXT,
            text_content TEXT,
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            source_type TEXT NOT NULL,
            source_creator_name TEXT,
            source_url TEXT,
            usage_permission TEXT NOT NULL,
            represents_creator INTEGER NOT NULL DEFAULT 0,
            approval_status TEXT NOT NULL,
            reference_purpose TEXT NOT NULL,
            notes TEXT,
            file_fingerprint TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_brand_profiles (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            brand_summary TEXT NOT NULL,
            visual_identity_json TEXT NOT NULL,
            preferred_composition_json TEXT NOT NULL,
            preferred_palette_json TEXT NOT NULL,
            typography_guidance_json TEXT NOT NULL,
            subject_guidance_json TEXT NOT NULL,
            expression_guidance_json TEXT NOT NULL,
            approved_patterns_json TEXT NOT NULL,
            rejected_patterns_json TEXT NOT NULL,
            prohibited_elements_json TEXT NOT NULL,
            platform_differences_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            UNIQUE (creator_id, profile_version),
            UNIQUE (creator_id, source_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS title_analysis_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            title_version_id TEXT NOT NULL,
            analyzer_version TEXT NOT NULL,
            status TEXT NOT NULL,
            configuration_json TEXT NOT NULL,
            creator_memory_snapshot_id TEXT,
            creator_language_snapshot_id TEXT,
            brand_profile_version INTEGER,
            source_fingerprint TEXT NOT NULL,
            warning_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (title_version_id) REFERENCES title_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_memory_snapshot_id) REFERENCES creator_profile_snapshots(id) ON DELETE SET NULL,
            FOREIGN KEY (creator_language_snapshot_id) REFERENCES creator_language_profile_snapshots(id) ON DELETE SET NULL,
            FOREIGN KEY (creator_id, brand_profile_version) REFERENCES packaging_brand_profiles(creator_id, profile_version) ON DELETE SET NULL,
            UNIQUE (creator_id, source_fingerprint, analyzer_version)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS title_analysis_metrics (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id) REFERENCES title_analysis_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_analysis_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            thumbnail_version_id TEXT NOT NULL,
            analyzer_version TEXT NOT NULL,
            status TEXT NOT NULL,
            configuration_json TEXT NOT NULL,
            creator_memory_snapshot_id TEXT,
            creator_language_snapshot_id TEXT,
            brand_profile_version INTEGER,
            source_fingerprint TEXT NOT NULL,
            warning_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (thumbnail_version_id) REFERENCES thumbnail_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (creator_memory_snapshot_id) REFERENCES creator_profile_snapshots(id) ON DELETE SET NULL,
            FOREIGN KEY (creator_language_snapshot_id) REFERENCES creator_language_profile_snapshots(id) ON DELETE SET NULL,
            FOREIGN KEY (creator_id, brand_profile_version) REFERENCES packaging_brand_profiles(creator_id, profile_version) ON DELETE SET NULL,
            UNIQUE (creator_id, source_fingerprint, analyzer_version)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_analysis_metrics (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id) REFERENCES thumbnail_analysis_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_pair_evaluations (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            title_version_id TEXT NOT NULL,
            thumbnail_version_id TEXT NOT NULL,
            publication_id TEXT,
            status TEXT NOT NULL,
            visual_quality_score REAL,
            content_alignment_score REAL,
            creator_brand_alignment_score REAL,
            audience_fit_score REAL,
            platform_fit_score REAL,
            historical_fit_score REAL,
            niche_fit_score REAL,
            differentiation_score REAL,
            clarity_score REAL,
            curiosity_score REAL,
            hierarchy_score REAL,
            complement_score REAL,
            authenticity_score REAL,
            promise_alignment_score REAL,
            evidence_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            risks_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            recommendation_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (title_version_id) REFERENCES title_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (thumbnail_version_id) REFERENCES thumbnail_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            UNIQUE (title_version_id, thumbnail_version_id, publication_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_frame_candidates (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            video_asset_id TEXT NOT NULL,
            timestamp_seconds REAL NOT NULL,
            frame_path TEXT NOT NULL,
            frame_fingerprint TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            sharpness_score REAL,
            brightness_score REAL,
            contrast_score REAL,
            face_presence INTEGER,
            motion_blur_score REAL,
            quality_status TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            creator_decision TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE CASCADE,
            UNIQUE (video_asset_id, timestamp_seconds, frame_fingerprint)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creative_concepts (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            concept_type TEXT NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            topic TEXT,
            title TEXT NOT NULL,
            premise TEXT NOT NULL,
            subject_description TEXT NOT NULL,
            action_description TEXT NOT NULL,
            composition_description TEXT NOT NULL,
            emotion_description TEXT NOT NULL,
            background_description TEXT NOT NULL,
            color_guidance TEXT NOT NULL,
            text_guidance TEXT NOT NULL,
            visual_hierarchy TEXT NOT NULL,
            relation_to_title TEXT NOT NULL,
            brand_alignment_notes TEXT NOT NULL,
            audience_fit_notes TEXT NOT NULL,
            platform_fit_notes TEXT NOT NULL,
            differentiation_notes TEXT NOT NULL,
            authenticity_notes TEXT NOT NULL,
            risks_json TEXT NOT NULL,
            reference_requirements_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creative_prompts (
            id TEXT PRIMARY KEY,
            concept_id TEXT NOT NULL,
            target_tool TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            negative_guidance TEXT,
            reference_instructions_json TEXT NOT NULL,
            tool_usage_notes_json TEXT NOT NULL,
            expected_output_notes TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            creator_approval_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (concept_id) REFERENCES creative_concepts(id) ON DELETE CASCADE,
            UNIQUE (concept_id, version_number)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS creative_prompt_references (
            id TEXT PRIMARY KEY,
            prompt_id TEXT NOT NULL,
            reference_asset_id TEXT,
            reference_role TEXT NOT NULL,
            required_level TEXT NOT NULL,
            instruction TEXT NOT NULL,
            risk_notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (prompt_id) REFERENCES creative_prompts(id) ON DELETE CASCADE,
            FOREIGN KEY (reference_asset_id) REFERENCES packaging_reference_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_reviews (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            thumbnail_version_id TEXT NOT NULL,
            title_version_id TEXT,
            publication_id TEXT,
            review_type TEXT NOT NULL,
            overall_status TEXT NOT NULL,
            visual_quality_json TEXT NOT NULL,
            content_alignment_json TEXT NOT NULL,
            brand_alignment_json TEXT NOT NULL,
            audience_fit_json TEXT NOT NULL,
            platform_fit_json TEXT NOT NULL,
            historical_fit_json TEXT NOT NULL,
            niche_fit_json TEXT NOT NULL,
            differentiation_json TEXT NOT NULL,
            strengths_json TEXT NOT NULL,
            weaknesses_json TEXT NOT NULL,
            keep_json TEXT NOT NULL,
            change_json TEXT NOT NULL,
            risks_json TEXT NOT NULL,
            final_recommendation TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (thumbnail_version_id) REFERENCES thumbnail_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (title_version_id) REFERENCES title_versions(id) ON DELETE SET NULL,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_decisions (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT,
            modified_value_json TEXT,
            decided_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packaging_experiment_links (
            id TEXT PRIMARY KEY,
            packaging_asset_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            assignment_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (packaging_asset_id) REFERENCES packaging_assets(id) ON DELETE CASCADE,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE CASCADE,
            FOREIGN KEY (assignment_id) REFERENCES experiment_assignments(id) ON DELETE SET NULL,
            UNIQUE (packaging_asset_id, experiment_id, assignment_id)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_assets_creator_id ON packaging_assets(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_assets_publication_id ON packaging_assets(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_assets_video_asset_id ON packaging_assets(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_assets_asset_type ON packaging_assets(asset_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_title_versions_packaging_asset_id ON title_versions(packaging_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_title_versions_source_fingerprint ON title_versions(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_versions_packaging_asset_id ON thumbnail_versions(packaging_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_versions_fingerprint ON thumbnail_versions(file_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_reference_assets_creator_id ON packaging_reference_assets(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_reference_assets_type ON packaging_reference_assets(reference_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_brand_profiles_creator_id ON packaging_brand_profiles(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_brand_profiles_fingerprint ON packaging_brand_profiles(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_title_analysis_runs_creator_id ON title_analysis_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_title_analysis_runs_title_version_id ON title_analysis_runs(title_version_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_title_analysis_metrics_run_id ON title_analysis_metrics(analysis_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_analysis_runs_creator_id ON thumbnail_analysis_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_analysis_runs_thumbnail_version_id ON thumbnail_analysis_runs(thumbnail_version_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_analysis_metrics_run_id ON thumbnail_analysis_metrics(analysis_run_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_pair_evaluations_creator_id ON packaging_pair_evaluations(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_pair_evaluations_title_version_id ON packaging_pair_evaluations(title_version_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_pair_evaluations_thumbnail_version_id ON packaging_pair_evaluations(thumbnail_version_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_frame_candidates_creator_id ON thumbnail_frame_candidates(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_frame_candidates_video_asset_id ON thumbnail_frame_candidates(video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creative_concepts_creator_id ON creative_concepts(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creative_prompts_concept_id ON creative_prompts(concept_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_creative_prompt_references_prompt_id ON creative_prompt_references(prompt_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_reviews_creator_id ON thumbnail_reviews(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_decisions_creator_id ON packaging_decisions(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_packaging_experiment_links_packaging_asset_id ON packaging_experiment_links(packaging_asset_id)")


def migration_21(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_connections (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            google_account_identifier TEXT,
            status TEXT NOT NULL CHECK (status IN ('disconnected', 'pending', 'connected', 'verified', 'revoked', 'error')),
            granted_scopes_json TEXT NOT NULL,
            credential_reference TEXT NOT NULL UNIQUE,
            connected_at TEXT NOT NULL,
            last_verified_at TEXT,
            disconnected_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_channels (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            youtube_channel_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            custom_url TEXT,
            country TEXT,
            published_at TEXT,
            thumbnail_url TEXT,
            subscriber_count INTEGER,
            video_count INTEGER,
            view_count INTEGER,
            hidden_subscriber_count INTEGER NOT NULL DEFAULT 0,
            selected_for_sync INTEGER NOT NULL DEFAULT 0,
            last_synced_at TEXT,
            remote_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES youtube_connections(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_remote_videos (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            youtube_video_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            content_type TEXT NOT NULL CHECK (content_type IN ('youtube_longform', 'youtube_short', 'probable_short', 'live', 'upcoming', 'unknown')),
            title TEXT NOT NULL,
            description TEXT,
            published_at TEXT NOT NULL,
            duration_seconds REAL,
            privacy_status TEXT,
            live_broadcast_content TEXT,
            default_language TEXT,
            default_audio_language TEXT,
            category_id TEXT,
            tags_json TEXT NOT NULL,
            thumbnail_metadata_json TEXT NOT NULL,
            remote_fingerprint TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES youtube_channels(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_video_thumbnails (
            id TEXT PRIMARY KEY,
            remote_video_id TEXT NOT NULL,
            thumbnail_type TEXT NOT NULL,
            remote_url TEXT NOT NULL,
            width INTEGER,
            height INTEGER,
            local_cache_path TEXT,
            remote_fingerprint TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (remote_video_id) REFERENCES youtube_remote_videos(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_sync_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            channel_id TEXT,
            sync_type TEXT NOT NULL CHECK (
                sync_type IN (
                    'connection_verify',
                    'channel_metadata',
                    'content_catalog',
                    'video_metadata',
                    'thumbnails_metadata',
                    'channel_analytics',
                    'video_analytics',
                    'incremental_sync',
                    'full_resync',
                    'repair_sync'
                )
            ),
            status TEXT NOT NULL CHECK (
                status IN ('queued', 'authenticating', 'listing_channels', 'syncing_content', 'syncing_metadata', 'syncing_analytics', 'linking_content', 'completed', 'completed_with_warnings', 'interrupted', 'failed', 'cancelled')
            ),
            configuration_json TEXT NOT NULL,
            cursor_json TEXT,
            discovered_count INTEGER NOT NULL DEFAULT 0,
            imported_count INTEGER NOT NULL DEFAULT 0,
            updated_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            quota_cost_estimate REAL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES youtube_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES youtube_channels(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_sync_items (
            id TEXT PRIMARY KEY,
            sync_run_id TEXT NOT NULL,
            remote_type TEXT NOT NULL,
            remote_id TEXT NOT NULL,
            local_type TEXT,
            local_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sync_run_id) REFERENCES youtube_sync_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_metric_imports (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            remote_video_id TEXT,
            sync_run_id TEXT NOT NULL,
            metric_scope TEXT NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT NOT NULL,
            comparable_window TEXT,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES youtube_channels(id) ON DELETE CASCADE,
            FOREIGN KEY (remote_video_id) REFERENCES youtube_remote_videos(id) ON DELETE SET NULL,
            FOREIGN KEY (sync_run_id) REFERENCES youtube_sync_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_metric_values (
            id TEXT PRIMARY KEY,
            metric_import_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            raw_metric_name TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT NOT NULL,
            dimensions_json TEXT NOT NULL,
            quality_status TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (metric_import_id) REFERENCES youtube_metric_imports(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_content_links (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            remote_video_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            link_method TEXT NOT NULL,
            confidence_level TEXT NOT NULL,
            status TEXT NOT NULL,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (remote_video_id) REFERENCES youtube_remote_videos(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_quota_usage (
            id TEXT PRIMARY KEY,
            connection_id TEXT NOT NULL,
            operation_key TEXT NOT NULL,
            estimated_cost REAL NOT NULL,
            request_count INTEGER NOT NULL,
            usage_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (connection_id) REFERENCES youtube_connections(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS youtube_sync_schedules (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            channel_id TEXT,
            schedule_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            interval_hours INTEGER,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES youtube_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES youtube_channels(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_connections_creator_id ON youtube_connections(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_channels_creator_id ON youtube_channels(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_channels_connection_id ON youtube_channels(connection_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_channels_creator_channel ON youtube_channels(creator_id, youtube_channel_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_remote_videos_creator_id ON youtube_remote_videos(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_remote_videos_channel_id ON youtube_remote_videos(channel_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_remote_videos_creator_video ON youtube_remote_videos(creator_id, youtube_video_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_video_thumbnails_remote_video_id ON youtube_video_thumbnails(remote_video_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_video_thumbnails_remote ON youtube_video_thumbnails(remote_video_id, thumbnail_type, remote_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_runs_creator_id ON youtube_sync_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_runs_connection_id ON youtube_sync_runs(connection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_runs_channel_id ON youtube_sync_runs(channel_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_sync_items_run_remote_action ON youtube_sync_items(sync_run_id, remote_type, remote_id, action)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_items_sync_run_id ON youtube_sync_items(sync_run_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_metric_imports_source_scope_dates ON youtube_metric_imports(source_fingerprint, metric_scope, date_start, date_end, channel_id, remote_video_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_metric_imports_creator_id ON youtube_metric_imports(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_metric_imports_channel_id ON youtube_metric_imports(channel_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_metric_values_import_metric_dimension ON youtube_metric_values(metric_import_id, metric_key, dimensions_json, raw_metric_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_metric_values_metric_import_id ON youtube_metric_values(metric_import_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_content_links_creator_remote_publication_video ON youtube_content_links(creator_id, remote_video_id, publication_id, video_asset_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_content_links_creator_id ON youtube_content_links(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_youtube_quota_usage_connection_operation_date ON youtube_quota_usage(connection_id, operation_key, usage_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_quota_usage_connection_id ON youtube_quota_usage(connection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_schedules_creator_id ON youtube_sync_schedules(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_schedules_connection_id ON youtube_sync_schedules(connection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_youtube_sync_schedules_channel_id ON youtube_sync_schedules(channel_id)")


def migration_22(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_profiles (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'reviewed', 'archived')),
            summary TEXT NOT NULL,
            evidence_quality TEXT NOT NULL,
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high', 'very_high')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_signals (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            channel_id TEXT,
            publication_id TEXT,
            remote_video_id TEXT,
            signal_type TEXT NOT NULL CHECK (signal_type IN ('acquisition', 'consumption', 'engagement', 'conversion', 'loyalty', 'affinity', 'geography', 'device', 'subscription_status', 'traffic_source', 'returning_behavior', 'cross_content_flow', 'data_quality')),
            signal_key TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT,
            period_start TEXT,
            period_end TEXT,
            observed_at TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT,
            dimensions_json TEXT NOT NULL,
            quality_status TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES youtube_channels(id) ON DELETE SET NULL,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (remote_video_id) REFERENCES youtube_remote_videos(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_segments (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            segment_type TEXT NOT NULL CHECK (segment_type IN ('system_defined', 'creator_defined', 'evidence_suggested')),
            description TEXT NOT NULL,
            scope TEXT NOT NULL CHECK (scope IN ('creator', 'platform', 'content', 'topic', 'format', 'journey', 'cohort', 'unknown')),
            platform TEXT,
            content_type TEXT,
            topic TEXT,
            lifecycle_stage TEXT,
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'reviewed', 'archived')),
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high', 'very_high')),
            confidence_score REAL,
            supporting_signal_count INTEGER NOT NULL DEFAULT 0,
            contradicting_signal_count INTEGER NOT NULL DEFAULT 0,
            first_observed_at TEXT,
            last_observed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_segment_definitions (
            id TEXT PRIMARY KEY,
            segment_id TEXT NOT NULL,
            rule_type TEXT NOT NULL,
            field_key TEXT NOT NULL,
            operator TEXT NOT NULL,
            value_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (segment_id) REFERENCES audience_segments(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_segment_evidence (
            id TEXT PRIMARY KEY,
            segment_id TEXT NOT NULL,
            signal_id TEXT,
            publication_id TEXT,
            analytics_finding_id TEXT,
            experiment_id TEXT,
            evidence_type TEXT NOT NULL CHECK (evidence_type IN ('metric', 'publication', 'analytics_finding', 'experiment', 'snapshot', 'review', 'quality', 'contradiction', 'inference', 'hypothesis')),
            supports_segment INTEGER NOT NULL DEFAULT 1,
            weight REAL NOT NULL DEFAULT 1.0,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (segment_id) REFERENCES audience_segments(id) ON DELETE CASCADE,
            FOREIGN KEY (signal_id) REFERENCES audience_signals(id) ON DELETE SET NULL,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (analytics_finding_id) REFERENCES analytics_findings(id) ON DELETE SET NULL,
            FOREIGN KEY (experiment_id) REFERENCES experiment_definitions(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_affinities (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            segment_id TEXT,
            affinity_type TEXT NOT NULL,
            target_key TEXT NOT NULL,
            target_value TEXT NOT NULL,
            platform TEXT,
            content_type TEXT,
            score REAL,
            supporting_example_count INTEGER NOT NULL DEFAULT 0,
            contradicting_example_count INTEGER NOT NULL DEFAULT 0,
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high', 'very_high')),
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'reviewed', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES audience_segments(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_journeys (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            entry_platform TEXT,
            entry_source TEXT,
            entry_content_type TEXT,
            next_step_type TEXT,
            conversion_type TEXT,
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'reviewed', 'archived')),
            confidence_level TEXT NOT NULL CHECK (confidence_level IN ('very_low', 'low', 'medium', 'high', 'very_high')),
            evidence_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_journey_steps (
            id TEXT PRIMARY KEY,
            journey_id TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT,
            action_type TEXT NOT NULL,
            metric_key TEXT,
            observed_value REAL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (journey_id) REFERENCES audience_journeys(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_profile_snapshots (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_version INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'reviewed', 'archived')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_reviews (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK (decision IN ('confirm', 'reject', 'needs_more_data', 'edit', 'merge', 'split', 'change_scope', 'deprecate')),
            previous_value_json TEXT,
            new_value_json TEXT,
            reason TEXT NOT NULL,
            reviewed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audience_model_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'collecting_signals', 'normalizing', 'building_segments', 'building_affinities', 'building_journeys', 'building_profile', 'completed', 'completed_with_warnings', 'interrupted', 'failed', 'cancelled')),
            configuration_json TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL,
            signal_count INTEGER NOT NULL DEFAULT 0,
            segment_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_profiles_creator_id ON audience_profiles(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_audience_profiles_creator_version ON audience_profiles(creator_id, profile_version)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_profiles_creator_version ON audience_profiles(creator_id, profile_version)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_signals_creator_id ON audience_signals(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_signals_platform ON audience_signals(platform)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_signals_publication_id ON audience_signals(publication_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_signals_creator_platform_key ON audience_signals(creator_id, platform, signal_type, signal_key, publication_id, remote_video_id, observed_at, source_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_segments_creator_id ON audience_segments(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_segments_scope ON audience_segments(creator_id, name, scope, platform, content_type, topic, lifecycle_stage)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_segment_definitions_segment_id ON audience_segment_definitions(segment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_segment_evidence_segment_id ON audience_segment_evidence(segment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_affinities_creator_id ON audience_affinities(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_affinities_target ON audience_affinities(creator_id, affinity_type, target_key, target_value, platform, content_type, segment_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_journeys_creator_id ON audience_journeys(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_journeys_target ON audience_journeys(creator_id, name, entry_platform, entry_source, entry_content_type, next_step_type, conversion_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_journey_steps_journey_id ON audience_journey_steps(journey_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_journey_steps_order ON audience_journey_steps(journey_id, step_order, platform, action_type, metric_key)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_profile_snapshots_creator_id ON audience_profile_snapshots(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_profile_snapshots_version_source ON audience_profile_snapshots(creator_id, profile_version, source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_reviews_creator_id ON audience_reviews(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_reviews_target ON audience_reviews(target_type, target_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_model_runs_creator_id ON audience_model_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audience_model_runs_fingerprint ON audience_model_runs(creator_id, source_fingerprint, configuration_json)")


def _ensure_analytics_v15_compatibility(connection: sqlite3.Connection) -> None:
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='analytics_metric_definitions'"
    ).fetchone()
    if not table_exists:
        return
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(analytics_metric_definitions)").fetchall()
    }
    if "applicability_json" not in columns:
        connection.execute(
            "ALTER TABLE analytics_metric_definitions ADD COLUMN applicability_json TEXT NOT NULL DEFAULT '[]'"
        )
    connection.execute(
        "UPDATE analytics_metric_definitions SET applicability_json = '[]' WHERE applicability_json IS NULL OR applicability_json = ''"
    )


def migration_23(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_connections (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            account_identifier TEXT,
            professional_account_type TEXT,
            status TEXT NOT NULL CHECK (status IN ('pending', 'connected', 'verified', 'disconnected', 'revoked', 'error')),
            granted_scopes_json TEXT NOT NULL,
            credential_reference TEXT NOT NULL,
            api_version TEXT NOT NULL,
            access_level TEXT,
            app_access_status TEXT NOT NULL CHECK (app_access_status IN ('development_mode', 'live_mode', 'standard_access', 'advanced_access', 'app_review_required', 'business_verification_required', 'tester_account_only', 'unknown')),
            connected_at TEXT NOT NULL,
            last_verified_at TEXT,
            disconnected_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_accounts (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            instagram_user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            name TEXT,
            biography TEXT,
            website TEXT,
            profile_picture_url TEXT,
            followers_count INTEGER,
            follows_count INTEGER,
            media_count INTEGER,
            account_type TEXT NOT NULL CHECK (account_type IN ('business', 'creator', 'personal', 'unknown')),
            selected_for_sync INTEGER NOT NULL DEFAULT 0,
            last_synced_at TEXT,
            remote_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES instagram_connections(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_remote_media (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            instagram_media_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            packaging_asset_id TEXT,
            media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video', 'carousel_album', 'reels', 'stories', 'live', 'unknown')),
            media_product_type TEXT,
            content_type TEXT NOT NULL CHECK (content_type IN ('instagram_reel', 'instagram_post', 'instagram_video', 'instagram_carousel', 'instagram_story', 'instagram_live', 'instagram_unknown')),
            caption TEXT,
            permalink TEXT,
            media_url TEXT,
            thumbnail_url TEXT,
            cover_url TEXT,
            timestamp TEXT NOT NULL,
            shortcode TEXT,
            children_count INTEGER,
            remote_fingerprint TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            remote_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES instagram_accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_carousel_children (
            id TEXT PRIMARY KEY,
            remote_media_id TEXT NOT NULL,
            instagram_child_id TEXT NOT NULL,
            child_order INTEGER NOT NULL,
            media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video', 'carousel_album', 'reels', 'stories', 'live', 'unknown')),
            media_url TEXT,
            thumbnail_url TEXT,
            remote_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (remote_media_id) REFERENCES instagram_remote_media(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_caption_versions (
            id TEXT PRIMARY KEY,
            remote_media_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            caption_text TEXT,
            source_fingerprint TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (remote_media_id) REFERENCES instagram_remote_media(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_cover_versions (
            id TEXT PRIMARY KEY,
            remote_media_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            cover_url TEXT,
            thumbnail_url TEXT,
            remote_fingerprint TEXT NOT NULL,
            packaging_asset_id TEXT,
            is_current INTEGER NOT NULL DEFAULT 1,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (remote_media_id) REFERENCES instagram_remote_media(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_sync_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            account_id TEXT,
            sync_type TEXT NOT NULL CHECK (sync_type IN ('connection_verify', 'account_metadata', 'media_catalog', 'media_metadata', 'carousel_children', 'account_insights', 'media_insights', 'incremental_sync', 'full_resync', 'repair_sync')),
            status TEXT NOT NULL CHECK (status IN ('queued', 'authenticating', 'verifying_account', 'syncing_profile', 'syncing_media', 'syncing_children', 'syncing_account_insights', 'syncing_media_insights', 'linking_content', 'completed', 'completed_with_warnings', 'interrupted', 'failed', 'cancelled')),
            configuration_json TEXT NOT NULL,
            cursor_json TEXT,
            discovered_count INTEGER NOT NULL DEFAULT 0,
            imported_count INTEGER NOT NULL DEFAULT 0,
            updated_count INTEGER NOT NULL DEFAULT 0,
            unchanged_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            estimated_usage TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES instagram_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES instagram_accounts(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_sync_items (
            id TEXT PRIMARY KEY,
            sync_run_id TEXT NOT NULL,
            remote_type TEXT NOT NULL,
            remote_id TEXT NOT NULL,
            local_type TEXT,
            local_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sync_run_id) REFERENCES instagram_sync_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_insight_imports (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            remote_media_id TEXT,
            sync_run_id TEXT NOT NULL,
            insight_scope TEXT NOT NULL CHECK (insight_scope IN ('account', 'media')),
            metric_period TEXT,
            date_start TEXT,
            date_end TEXT,
            comparable_window TEXT,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES instagram_accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (remote_media_id) REFERENCES instagram_remote_media(id) ON DELETE SET NULL,
            FOREIGN KEY (sync_run_id) REFERENCES instagram_sync_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_insight_values (
            id TEXT PRIMARY KEY,
            insight_import_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            raw_metric_name TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT,
            period TEXT,
            dimensions_json TEXT NOT NULL,
            breakdowns_json TEXT NOT NULL,
            quality_status TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (insight_import_id) REFERENCES instagram_insight_imports(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_content_links (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            remote_media_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            packaging_asset_id TEXT,
            link_method TEXT NOT NULL CHECK (link_method IN ('exact_instagram_id', 'exact_permalink', 'manual', 'normalized_caption_and_date', 'media_timestamp', 'metadata_match', 'probable_match')),
            confidence_level TEXT NOT NULL,
            status TEXT NOT NULL,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (remote_media_id) REFERENCES instagram_remote_media(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_rate_limit_usage (
            id TEXT PRIMARY KEY,
            connection_id TEXT NOT NULL,
            operation_key TEXT NOT NULL,
            estimated_usage TEXT,
            request_count INTEGER NOT NULL,
            usage_date TEXT NOT NULL,
            headers_snapshot_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (connection_id) REFERENCES instagram_connections(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS instagram_sync_schedules (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            account_id TEXT,
            schedule_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_hours INTEGER,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES instagram_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (account_id) REFERENCES instagram_accounts(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_connections_creator_id ON instagram_connections(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_connections_provider ON instagram_connections(provider)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_accounts_creator_id ON instagram_accounts(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_accounts_creator_user ON instagram_accounts(creator_id, instagram_user_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_accounts_connection_id ON instagram_accounts(connection_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_remote_media_creator_id ON instagram_remote_media(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_remote_media_creator_remote ON instagram_remote_media(creator_id, instagram_media_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_remote_media_account_id ON instagram_remote_media(account_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_carousel_children_remote_media_id ON instagram_carousel_children(remote_media_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_carousel_children_remote_child ON instagram_carousel_children(remote_media_id, instagram_child_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_caption_versions_remote_version ON instagram_caption_versions(remote_media_id, version_number)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_caption_versions_remote_media_id ON instagram_caption_versions(remote_media_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_cover_versions_remote_version ON instagram_cover_versions(remote_media_id, version_number)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_cover_versions_remote_media_id ON instagram_cover_versions(remote_media_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_sync_runs_creator_id ON instagram_sync_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_sync_runs_connection_id ON instagram_sync_runs(connection_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_sync_items_run_remote_action ON instagram_sync_items(sync_run_id, remote_type, remote_id, action)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_sync_items_sync_run_id ON instagram_sync_items(sync_run_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_insight_imports_source ON instagram_insight_imports(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_insight_imports_creator_id ON instagram_insight_imports(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_insight_values_import_metric_dimension ON instagram_insight_values(insight_import_id, metric_key, dimensions_json, raw_metric_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_insight_values_import_id ON instagram_insight_values(insight_import_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_content_links_creator_remote_publication_video_package ON instagram_content_links(creator_id, remote_media_id, IFNULL(publication_id, ''), IFNULL(video_asset_id, ''), IFNULL(packaging_asset_id, ''))")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_content_links_creator_id ON instagram_content_links(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_rate_limit_usage_connection_operation_date ON instagram_rate_limit_usage(connection_id, operation_key, usage_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_rate_limit_usage_connection_id ON instagram_rate_limit_usage(connection_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_instagram_sync_schedules_creator_connection_schedule ON instagram_sync_schedules(creator_id, connection_id, schedule_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_sync_schedules_creator_id ON instagram_sync_schedules(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_instagram_sync_schedules_connection_id ON instagram_sync_schedules(connection_id)")


def migration_24(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_connections (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'connected', 'verified', 'disconnected', 'revoked', 'error')),
            open_id TEXT,
            union_id TEXT,
            account_identifier TEXT,
            granted_scopes_json TEXT NOT NULL,
            credential_reference TEXT NOT NULL,
            api_version TEXT NOT NULL,
            access_level TEXT,
            connected_at TEXT NOT NULL,
            last_verified_at TEXT,
            disconnected_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_profiles (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            open_id TEXT NOT NULL,
            union_id TEXT,
            display_name TEXT,
            username TEXT,
            avatar_url TEXT,
            bio_description TEXT,
            profile_deep_link TEXT,
            profile_web_link TEXT,
            is_verified INTEGER,
            follower_count INTEGER,
            following_count INTEGER,
            likes_count INTEGER,
            video_count INTEGER,
            selected_for_sync INTEGER NOT NULL DEFAULT 0,
            last_synced_at TEXT,
            remote_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES tiktok_connections(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_remote_videos (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            tiktok_video_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            packaging_asset_id TEXT,
            title TEXT,
            video_description TEXT,
            create_time TEXT NOT NULL,
            duration_seconds INTEGER,
            width INTEGER,
            height INTEGER,
            share_url TEXT,
            embed_link TEXT,
            cover_image_url TEXT,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            view_count INTEGER,
            remote_fingerprint TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            remote_status TEXT NOT NULL CHECK (remote_status IN ('public', 'unavailable', 'no_longer_returned', 'access_changed', 'unknown')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES tiktok_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL,
            FOREIGN KEY (packaging_asset_id) REFERENCES packaging_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_video_text_versions (
            id TEXT PRIMARY KEY,
            remote_video_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            title_text TEXT,
            description_text TEXT,
            source_fingerprint TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 1,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (remote_video_id) REFERENCES tiktok_remote_videos(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_cover_versions (
            id TEXT PRIMARY KEY,
            remote_video_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            cover_image_url TEXT,
            remote_fingerprint TEXT NOT NULL,
            packaging_asset_id TEXT,
            is_current INTEGER NOT NULL DEFAULT 1,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (remote_video_id) REFERENCES tiktok_remote_videos(id) ON DELETE CASCADE,
            FOREIGN KEY (packaging_asset_id) REFERENCES packaging_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_sync_runs (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            profile_id TEXT,
            sync_type TEXT NOT NULL CHECK (sync_type IN ('connection_verify', 'profile_metadata', 'profile_stats', 'video_catalog', 'video_metadata', 'public_metrics', 'incremental_sync', 'full_resync', 'repair_sync', 'cover_refresh')),
            status TEXT NOT NULL CHECK (status IN ('queued', 'authenticating', 'verifying_profile', 'syncing_profile', 'syncing_videos', 'refreshing_videos', 'importing_metrics', 'linking_content', 'completed', 'completed_with_warnings', 'interrupted', 'failed', 'cancelled')),
            configuration_json TEXT NOT NULL,
            cursor_json TEXT,
            discovered_count INTEGER NOT NULL DEFAULT 0,
            imported_count INTEGER NOT NULL DEFAULT 0,
            updated_count INTEGER NOT NULL DEFAULT 0,
            unchanged_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            estimated_usage TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES tiktok_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES tiktok_profiles(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_sync_items (
            id TEXT PRIMARY KEY,
            sync_run_id TEXT NOT NULL,
            remote_type TEXT NOT NULL,
            remote_id TEXT NOT NULL,
            local_type TEXT,
            local_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sync_run_id) REFERENCES tiktok_sync_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_metric_imports (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            remote_video_id TEXT,
            sync_run_id TEXT NOT NULL,
            metric_scope TEXT NOT NULL CHECK (metric_scope IN ('profile', 'video', 'manual_snapshot')),
            source_type TEXT NOT NULL CHECK (source_type IN ('tiktok_display_api', 'tiktok_manual_csv', 'tiktok_manual_xlsx', 'manual_other')),
            observed_at TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            comparable_window TEXT,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES tiktok_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (remote_video_id) REFERENCES tiktok_remote_videos(id) ON DELETE SET NULL,
            FOREIGN KEY (sync_run_id) REFERENCES tiktok_sync_runs(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_metric_values (
            id TEXT PRIMARY KEY,
            metric_import_id TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            raw_metric_name TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT,
            dimensions_json TEXT NOT NULL,
            quality_status TEXT NOT NULL,
            warning_codes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (metric_import_id) REFERENCES tiktok_metric_imports(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_content_links (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            remote_video_id TEXT NOT NULL,
            publication_id TEXT,
            video_asset_id TEXT,
            packaging_asset_id TEXT,
            link_method TEXT NOT NULL CHECK (link_method IN ('exact_tiktok_id', 'exact_share_url', 'manual', 'normalized_description_and_date', 'create_time_match', 'metadata_match', 'probable_match')),
            confidence_level TEXT NOT NULL,
            status TEXT NOT NULL,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (remote_video_id) REFERENCES tiktok_remote_videos(id) ON DELETE CASCADE,
            FOREIGN KEY (publication_id) REFERENCES analytics_publications(id) ON DELETE SET NULL,
            FOREIGN KEY (video_asset_id) REFERENCES video_assets(id) ON DELETE SET NULL,
            FOREIGN KEY (packaging_asset_id) REFERENCES packaging_assets(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_rate_limit_usage (
            id TEXT PRIMARY KEY,
            connection_id TEXT NOT NULL,
            operation_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            request_count INTEGER NOT NULL,
            estimated_usage TEXT,
            window_started_at TEXT,
            response_headers_json TEXT,
            usage_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (connection_id) REFERENCES tiktok_connections(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tiktok_sync_schedules (
            id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            profile_id TEXT,
            schedule_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_hours INTEGER,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES creators(id) ON DELETE CASCADE,
            FOREIGN KEY (connection_id) REFERENCES tiktok_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES tiktok_profiles(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_connections_creator_id ON tiktok_connections(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_connections_status ON tiktok_connections(status)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_connections_creator_open_id ON tiktok_connections(creator_id, open_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_profiles_creator_id ON tiktok_profiles(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_profiles_connection_id ON tiktok_profiles(connection_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_profiles_creator_open_id ON tiktok_profiles(creator_id, open_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_remote_videos_creator_id ON tiktok_remote_videos(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_remote_videos_profile_id ON tiktok_remote_videos(profile_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_remote_videos_creator_video ON tiktok_remote_videos(creator_id, tiktok_video_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_video_text_versions_remote_video_id ON tiktok_video_text_versions(remote_video_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_video_text_versions_remote_version ON tiktok_video_text_versions(remote_video_id, version_number)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_cover_versions_remote_video_id ON tiktok_cover_versions(remote_video_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_cover_versions_remote_version ON tiktok_cover_versions(remote_video_id, version_number)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_sync_runs_creator_id ON tiktok_sync_runs(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_sync_runs_connection_id ON tiktok_sync_runs(connection_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_sync_items_run_remote_action ON tiktok_sync_items(sync_run_id, remote_type, remote_id, action)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_sync_items_sync_run_id ON tiktok_sync_items(sync_run_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_metric_imports_source ON tiktok_metric_imports(source_fingerprint)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_metric_imports_creator_id ON tiktok_metric_imports(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_metric_imports_profile_id ON tiktok_metric_imports(profile_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_metric_values_import_metric_dimension ON tiktok_metric_values(metric_import_id, metric_key, dimensions_json, raw_metric_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_metric_values_import_id ON tiktok_metric_values(metric_import_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_content_links_creator_remote_publication_video_package ON tiktok_content_links(creator_id, remote_video_id, IFNULL(publication_id, ''), IFNULL(video_asset_id, ''), IFNULL(packaging_asset_id, ''))")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_content_links_creator_id ON tiktok_content_links(creator_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_rate_limit_usage_connection_operation_date ON tiktok_rate_limit_usage(connection_id, operation_key, usage_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_rate_limit_usage_connection_id ON tiktok_rate_limit_usage(connection_id)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_sync_schedules_creator_connection_schedule ON tiktok_sync_schedules(creator_id, connection_id, schedule_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_sync_schedules_creator_id ON tiktok_sync_schedules(creator_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tiktok_sync_schedules_connection_id ON tiktok_sync_schedules(connection_id)")


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
    Migration(version=14, name="subtitle_deliveries"),
    Migration(version=15, name="analytics_data_foundation"),
    Migration(version=16, name="analytics_lab"),
    Migration(version=17, name="experiments_learning"),
    Migration(version=18, name="creator_memory"),
    Migration(version=19, name="creator_language"),
    Migration(version=20, name="creative_packaging"),
    Migration(version=21, name="youtube_read_only_integration"),
    Migration(version=22, name="audience_model_foundation"),
    Migration(version=23, name="instagram_read_only_integration"),
    Migration(version=24, name="tiktok_read_only_integration"),
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
                elif migration.version == 14:
                    migration_14(connection)
                elif migration.version == 15:
                    migration_15(connection)
                elif migration.version == 16:
                    migration_16(connection)
                elif migration.version == 17:
                    migration_17(connection)
                elif migration.version == 18:
                    migration_18(connection)
                elif migration.version == 19:
                    migration_19(connection)
                elif migration.version == 20:
                    migration_20(connection)
                elif migration.version == 21:
                    migration_21(connection)
                elif migration.version == 22:
                    migration_22(connection)
                elif migration.version == 23:
                    migration_23(connection)
                elif migration.version == 24:
                    migration_24(connection)
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
    _ensure_analytics_v15_compatibility(connection)
