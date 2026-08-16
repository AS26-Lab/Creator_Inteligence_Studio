"""Carga y validacion de configuracion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.shared.paths import resolve_configured_path

ALLOWED_ENVIRONMENTS = {"development", "production", "test"}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
ALLOWED_BACKENDS = {"cuda", "cpu"}


class SettingsError(ValueError):
    """Error de configuracion con mensaje entendible."""


@dataclass(frozen=True)
class AppSettings:
    """Configuracion minima de la aplicacion."""

    application_name: str
    environment: str
    log_level: str
    data_directory: str
    logs_directory: str
    models_directory: str
    artifacts_directory: str
    preferred_compute_backend: str
    allow_cpu_basic_mode: bool
    external_ai_enabled: bool
    database_filename: str = "creator_intelligence_studio.db"
    database_timeout_seconds: float = 5.0
    ffmpeg_path: str | None = None
    ffprobe_path: str | None = None
    ffmpeg_bin_directory: str | None = None
    audio_normalization_sample_rate_hz: int = 16000
    audio_extraction_timeout_seconds: float = 60.0
    audio_cache_version: str = "v1"
    preferred_audio_language: str | None = None
    youtube_oauth_client_id: str | None = None

    @classmethod
    def from_file(cls, config_path: Path) -> "AppSettings":
        """Carga la configuracion desde JSON."""

        try:
            raw_text = config_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise SettingsError(
                f"No se encontro el archivo de configuracion: {config_path}"
            ) from exc

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise SettingsError(
                f"El archivo de configuracion no contiene JSON valido: {config_path}"
            ) from exc

        if not isinstance(payload, dict):
            raise SettingsError("La configuracion debe ser un objeto JSON.")

        def require_str(key: str) -> str:
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                raise SettingsError(f"El campo '{key}' debe ser una cadena no vacia.")
            return value.strip()

        def require_bool(key: str) -> bool:
            value = payload.get(key)
            if not isinstance(value, bool):
                raise SettingsError(f"El campo '{key}' debe ser booleano.")
            return value

        def optional_str(key: str, default: str) -> str:
            value = payload.get(key, default)
            if not isinstance(value, str) or not value.strip():
                return default
            return value.strip()

        def optional_path(key: str) -> str | None:
            value = payload.get(key)
            if value is None:
                return None
            if not isinstance(value, str) or not value.strip():
                raise SettingsError(f"El campo '{key}' debe ser una cadena no vacia.")
            return value.strip()

        def optional_text(key: str) -> str | None:
            value = payload.get(key)
            if value is None:
                return None
            if not isinstance(value, str):
                raise SettingsError(f"El campo '{key}' debe ser una cadena.")
            text = value.strip()
            return text or None

        def optional_int(key: str, default: int) -> int:
            value = payload.get(key, default)
            if isinstance(value, bool):
                raise SettingsError(f"El campo '{key}' debe ser entero.")
            if isinstance(value, int):
                return value
            raise SettingsError(f"El campo '{key}' debe ser entero.")

        def optional_number(key: str, default: float) -> float:
            value = payload.get(key, default)
            if isinstance(value, bool):
                raise SettingsError(f"El campo '{key}' debe ser numérico.")
            if isinstance(value, (int, float)):
                return float(value)
            raise SettingsError(f"El campo '{key}' debe ser numérico.")

        settings = cls(
            application_name=require_str("application_name"),
            environment=require_str("environment"),
            log_level=require_str("log_level").upper(),
            data_directory=require_str("data_directory"),
            logs_directory=require_str("logs_directory"),
            models_directory=require_str("models_directory"),
            artifacts_directory=require_str("artifacts_directory"),
            preferred_compute_backend=require_str("preferred_compute_backend").lower(),
            allow_cpu_basic_mode=require_bool("allow_cpu_basic_mode"),
            external_ai_enabled=require_bool("external_ai_enabled"),
            database_filename=optional_str("database_filename", "creator_intelligence_studio.db"),
            database_timeout_seconds=optional_number("database_timeout_seconds", 5.0),
            ffmpeg_path=optional_path("ffmpeg_path"),
            ffprobe_path=optional_path("ffprobe_path"),
            ffmpeg_bin_directory=optional_path("ffmpeg_bin_directory"),
            audio_normalization_sample_rate_hz=optional_int("audio_normalization_sample_rate_hz", 16000),
            audio_extraction_timeout_seconds=optional_number("audio_extraction_timeout_seconds", 60.0),
            audio_cache_version=optional_str("audio_cache_version", "v1"),
            preferred_audio_language=optional_path("preferred_audio_language"),
            youtube_oauth_client_id=optional_text("youtube_oauth_client_id"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Valida la configuracion cargada."""

        if self.environment not in ALLOWED_ENVIRONMENTS:
            raise SettingsError(
                f"environment no es valido: '{self.environment}'. "
                f"Valores permitidos: {sorted(ALLOWED_ENVIRONMENTS)}"
            )
        if self.log_level not in ALLOWED_LOG_LEVELS:
            raise SettingsError(
                f"log_level no es valido: '{self.log_level}'. "
                f"Valores permitidos: {sorted(ALLOWED_LOG_LEVELS)}"
            )
        if self.preferred_compute_backend not in ALLOWED_BACKENDS:
            raise SettingsError(
                f"preferred_compute_backend no es valido: "
                f"'{self.preferred_compute_backend}'. "
                f"Valores permitidos: {sorted(ALLOWED_BACKENDS)}"
            )
        if self.database_timeout_seconds <= 0:
            raise SettingsError("database_timeout_seconds debe ser mayor que cero.")
        if self.audio_normalization_sample_rate_hz <= 0:
            raise SettingsError("audio_normalization_sample_rate_hz debe ser mayor que cero.")
        if self.audio_extraction_timeout_seconds <= 0:
            raise SettingsError("audio_extraction_timeout_seconds debe ser mayor que cero.")
        if not self.audio_cache_version.strip():
            raise SettingsError("audio_cache_version no puede estar vacio.")

    def resolved_directories(self, project_root: Path) -> dict[str, Path]:
        """Resuelve directorios relativos al proyecto."""

        return {
            "data_directory": resolve_configured_path(project_root, self.data_directory),
            "logs_directory": resolve_configured_path(project_root, self.logs_directory),
            "models_directory": resolve_configured_path(project_root, self.models_directory),
            "artifacts_directory": resolve_configured_path(
                project_root, self.artifacts_directory
            ),
        }

    def resolved_media_tool_paths(self, project_root: Path) -> dict[str, Path | None]:
        """Resuelve rutas configuradas para herramientas multimedia."""

        def resolve_optional_path(configured_value: str | None) -> Path | None:
            if configured_value is None:
                return None
            return resolve_configured_path(project_root, configured_value)

        return {
            "ffmpeg_path": resolve_optional_path(self.ffmpeg_path),
            "ffprobe_path": resolve_optional_path(self.ffprobe_path),
            "ffmpeg_bin_directory": resolve_optional_path(self.ffmpeg_bin_directory),
        }


def load_settings(config_path: Path) -> AppSettings:
    """Carga la configuracion del proyecto."""

    return AppSettings.from_file(config_path)
