"""Migraciones SQLite minimas y reales."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3

from creator_intelligence_studio.infrastructure.persistence.database import DatabaseError


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
            prepared_audio_asset_id TEXT NOT NULL,
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


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="initial_schema"),
    Migration(version=2, name="video_inspections"),
    Migration(version=3, name="prepared_audio_assets"),
    Migration(version=4, name="transcriptions"),
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
