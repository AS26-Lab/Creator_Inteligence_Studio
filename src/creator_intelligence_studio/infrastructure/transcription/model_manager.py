"""Gestion de caché y descarga de modelos de transcripcion."""

from __future__ import annotations

import logging
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from uuid import uuid4

from creator_intelligence_studio.domain.transcription import DEFAULT_TRANSCRIPTION_MODELS, PROFILE_TO_MODEL
from creator_intelligence_studio.domain.transcription.errors import TranscriptionBackendError
from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionModelInfo,
    TranscriptionModelStatus,
    TranscriptionProgress,
)


def _repo_id(model_name: str) -> str:
    return f"Systran/faster-whisper-{model_name}"


@dataclass(slots=True)
class TranscriptionModelManager:
    """Resuelve rutas de modelos, estados de caché y descargas atomicas."""

    models_root: Path
    downloader: Callable[..., object] | None = None
    logger: logging.Logger | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _model_locks: dict[str, threading.Lock] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.models_root.mkdir(parents=True, exist_ok=True)
        if self.logger is None:
            self.logger = logging.getLogger("creator_intelligence_studio.transcription")

    @property
    def cache_root(self) -> Path:
        return self.models_root / "transcription" / "faster-whisper"

    def resolve_model_path(self, model_name: str) -> Path:
        return self.cache_root / model_name

    def download_root(self, model_name: str) -> str:
        return str(self.resolve_model_path(model_name))

    def is_downloaded(self, model_name: str) -> bool:
        return self.get_model_status(model_name).status == TranscriptionModelStatus.INSTALLED

    def list_models(self) -> tuple[TranscriptionModelInfo, ...]:
        infos: list[TranscriptionModelInfo] = []
        for model_name in DEFAULT_TRANSCRIPTION_MODELS:
            infos.append(self.get_model_status(model_name))
        return tuple(infos)

    def get_model_status(self, model_name: str) -> TranscriptionModelInfo:
        model_name = model_name.strip().lower()
        path = self.resolve_model_path(model_name)
        status, notes, error_code, error_message = self._inspect_cache(path, model_name)
        size_bytes = self._directory_size(path) if path.exists() else None
        profile = next((profile for profile, name in PROFILE_TO_MODEL.items() if name == model_name), model_name)
        return TranscriptionModelInfo(
            model_name=model_name,
            profile=profile,
            path=str(path),
            installed=status == TranscriptionModelStatus.INSTALLED,
            size_bytes=size_bytes,
            notes=notes,
            status=status,
            error_code=error_code,
            error_message=error_message,
        )

    def verify_model(self, model_name: str) -> TranscriptionModelInfo:
        """Verifica que el modelo pueda cargarse sin descargarlo de nuevo."""

        model_name = model_name.strip().lower()
        path = self.resolve_model_path(model_name)
        status, notes, error_code, error_message = self._inspect_cache(path, model_name, allow_verification=True)
        if status != TranscriptionModelStatus.INSTALLED:
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=next((profile for profile, name in PROFILE_TO_MODEL.items() if name == model_name), model_name),
                path=str(path),
                installed=False,
                size_bytes=self._directory_size(path) if path.exists() else None,
                notes=notes,
                status=status,
                error_code=error_code,
                error_message=error_message,
            )
        marker = self._download_marker(model_name)
        if marker.exists():
            try:
                marker.unlink()
            except OSError:
                pass
        current = self.get_model_status(model_name)
        try:
            from faster_whisper import WhisperModel

            WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(path),
            )
        except Exception as exc:
            message = str(exc)
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=current.profile,
                path=str(path),
                installed=False,
                size_bytes=current.size_bytes,
                notes="El modelo esta presente pero no puede verificarse con el backend local.",
                status=TranscriptionModelStatus.INCOMPATIBLE,
                error_code="model_incompatible",
                error_message=message,
            )
        return TranscriptionModelInfo(
            model_name=model_name,
            profile=current.profile,
            path=str(path),
            installed=True,
            size_bytes=current.size_bytes,
            notes="Modelo instalado y verificado localmente.",
            status=TranscriptionModelStatus.INSTALLED,
        )

    def download_model(
        self,
        model_name: str,
        *,
        force: bool = False,
        progress_callback: Callable[[TranscriptionProgress], None] | None = None,
        cancellation_token=None,
    ) -> TranscriptionModelInfo:
        """Descarga el modelo en una caché temporal y lo publica de forma atomica."""

        model_name = model_name.strip().lower()
        target = self.resolve_model_path(model_name)
        current = self.get_model_status(model_name)
        if current.status == TranscriptionModelStatus.INSTALLED and not force:
            return self.verify_model(model_name)

        with self._model_lock(model_name):
            current = self.get_model_status(model_name)
            if current.status == TranscriptionModelStatus.INSTALLED and not force:
                return self.verify_model(model_name)

            if current.status == TranscriptionModelStatus.INSTALLED and force:
                self.remove_model(model_name)
            elif current.status == TranscriptionModelStatus.DOWNLOADING and target.exists():
                verified = self.verify_model(model_name)
                if verified.status == TranscriptionModelStatus.INSTALLED and not force:
                    return verified

            if current.status in {TranscriptionModelStatus.CORRUPT, TranscriptionModelStatus.INCOMPLETE, TranscriptionModelStatus.ERROR} and target.exists():
                self._safe_rmtree(target)

            marker = self._download_marker(model_name)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("downloading", encoding="utf-8")
            staging_root = self.cache_root / ".downloads" / f"{model_name}-{uuid4().hex}"
            staging_root.parent.mkdir(parents=True, exist_ok=True)
            staging_root.mkdir(parents=True, exist_ok=True)
            if progress_callback is not None:
                progress_callback(
                    TranscriptionProgress(
                        phase="Descargando modelo",
                        approximate=True,
                        message=f"Destino: {target}",
                    )
                )
            try:
                downloader = self.downloader
                if downloader is None:
                    from huggingface_hub import snapshot_download

                    downloader = snapshot_download
                downloader(
                    repo_id=_repo_id(model_name),
                    cache_dir=str(staging_root),
                    local_files_only=False,
                    resume_download=True,
                )
                if cancellation_token is not None and cancellation_token.cancelled():
                    raise TranscriptionBackendError("La descarga fue cancelada por el usuario.")
                verification = self._inspect_cache(staging_root, model_name, allow_verification=True)
                if verification[0] != TranscriptionModelStatus.INSTALLED:
                    raise TranscriptionBackendError(
                        verification[3] or "La descarga no produjo una caché de modelo valida."
                    )
                if target.exists():
                    self._safe_rmtree(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                staging_root.rename(target)
                return self.verify_model(model_name)
            except Exception as exc:
                self.logger.warning("No se pudo descargar el modelo %s: %s", model_name, exc)
                self._safe_rmtree(staging_root)
                return TranscriptionModelInfo(
                    model_name=model_name,
                    profile=current.profile,
                    path=str(target),
                    installed=False,
                    size_bytes=None,
                    notes="La descarga del modelo fallo.",
                    status=TranscriptionModelStatus.ERROR,
                    error_code="download_failed",
                    error_message=str(exc),
                )
            finally:
                if marker.exists():
                    try:
                        marker.unlink()
                    except OSError:
                        pass

    def remove_model(self, model_name: str) -> bool:
        """Elimina solo la caché administrada por la aplicacion."""

        model_name = model_name.strip().lower()
        target = self.resolve_model_path(model_name)
        marker = self._download_marker(model_name)
        removed = False
        if marker.exists():
            try:
                marker.unlink()
                removed = True
            except OSError:
                pass
        if target.exists():
            self._safe_rmtree(target)
            removed = True
        return removed

    def _model_lock(self, model_name: str) -> threading.Lock:
        with self._lock:
            lock = self._model_locks.get(model_name)
            if lock is None:
                lock = threading.Lock()
                self._model_locks[model_name] = lock
            return lock

    def _download_marker(self, model_name: str) -> Path:
        return self.cache_root / f".{model_name}.downloading"

    def _repo_cache_dir(self, path: Path, model_name: str) -> Path:
        return path / f"models--Systran--faster-whisper-{model_name}"

    def _snapshot_dir(self, repo_cache_dir: Path) -> Path | None:
        snapshots_root = repo_cache_dir / "snapshots"
        if not snapshots_root.exists():
            return None
        snapshots = [path for path in snapshots_root.iterdir() if path.is_dir()]
        if not snapshots:
            return None
        return sorted(snapshots)[0]

    def _snapshot_has_required_files(self, snapshot_dir: Path) -> bool:
        required = {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt"}
        present = {path.name for path in snapshot_dir.iterdir() if path.is_file()}
        return required.issubset(present)

    def _inspect_cache(
        self,
        path: Path,
        model_name: str,
        *,
        allow_verification: bool = False,
    ) -> tuple[TranscriptionModelStatus, str | None, str | None, str | None]:
        marker = self._download_marker(model_name)
        if not path.exists():
            if marker.exists():
                return TranscriptionModelStatus.DOWNLOADING, "Modelo descargandose en caché controlada.", None, None
            return TranscriptionModelStatus.NOT_INSTALLED, "Modelo no instalado.", None, None
        if not path.is_dir():
            return TranscriptionModelStatus.CORRUPT, "La ruta del modelo no es un directorio valido.", "model_corrupt", "La ruta del modelo no es un directorio valido."

        repo_cache_dir = self._repo_cache_dir(path, model_name)
        if not repo_cache_dir.exists():
            return TranscriptionModelStatus.INCOMPLETE, "La caché no contiene archivos del modelo.", "model_incomplete", "Faltan archivos del modelo."

        snapshot_dir = self._snapshot_dir(repo_cache_dir)
        if snapshot_dir is None:
            return TranscriptionModelStatus.INCOMPLETE, "La caché no contiene un snapshot completo.", "model_incomplete", "La caché no contiene un snapshot completo."

        if not self._snapshot_has_required_files(snapshot_dir):
            return TranscriptionModelStatus.INCOMPLETE, "El snapshot existe pero le faltan archivos minimos.", "model_incomplete", "El snapshot existe pero le faltan archivos minimos."

        if allow_verification:
            try:
                from faster_whisper import WhisperModel

                WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(path),
                )
            except Exception as exc:
                message = str(exc)
                if "compute" in message.lower() or "unsupported" in message.lower() or "incompatible" in message.lower():
                    return TranscriptionModelStatus.INCOMPATIBLE, "El modelo no es compatible con el backend local.", "model_incompatible", message
                return TranscriptionModelStatus.CORRUPT, "El snapshot existe pero no puede cargarse.", "model_corrupt", message

        return TranscriptionModelStatus.INSTALLED, "Modelo disponible en caché local.", None, None

    @staticmethod
    def _directory_size(path: Path) -> int | None:
        if not path.exists():
            return None
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                try:
                    total += file_path.stat().st_size
                except OSError:
                    continue
        return total

    @staticmethod
    def _safe_rmtree(path: Path) -> None:
        if not path.exists():
            return
        shutil.rmtree(path, ignore_errors=True)
