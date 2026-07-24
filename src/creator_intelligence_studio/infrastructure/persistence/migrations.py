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
