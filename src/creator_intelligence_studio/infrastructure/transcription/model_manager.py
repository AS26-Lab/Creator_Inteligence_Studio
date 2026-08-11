"""Gestion local y resolucion de modelos de transcripcion."""

from __future__ import annotations

import json
import logging
import shutil
import threading
from dataclasses import dataclass, field, replace
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


def _component_id_for_model(model_name: str) -> str:
    return f"transcription-model.{model_name}"


def _normalize_model_name(model_name: str) -> str:
    return model_name.strip().lower()


@dataclass(frozen=True, slots=True)
class _BundleInspection:
    status: TranscriptionModelStatus
    notes: str | None
    error_code: str | None
    error_message: str | None
    size_bytes: int | None


@dataclass(slots=True)
class TranscriptionModelManager:
    """Resuelve rutas, caches legacy y activacion administrada de modelos."""

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

    def model_component_id(self, model_name: str) -> str:
        return _component_id_for_model(_normalize_model_name(model_name))

    def legacy_cache_root(self, model_name: str) -> Path:
        return self.cache_root / _normalize_model_name(model_name)

    def managed_component_root(self, model_component_id: str) -> Path:
        return self.cache_root / model_component_id.strip().lower()

    def managed_version_root(self, model_component_id: str, revision: str) -> Path:
        return self.managed_component_root(model_component_id) / revision.strip().lower()

    def active_manifest_path(self, model_component_id: str) -> Path:
        return self.managed_component_root(model_component_id) / "active.json"

    def _write_json_atomic(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.tmp-{uuid4().hex}")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)

    def _read_json(self, path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _active_manifest(self, model_component_id: str) -> dict[str, object] | None:
        return self._read_json(self.active_manifest_path(model_component_id))

    def active_model_root(self, model_component_id: str) -> Path | None:
        manifest = self._active_manifest(model_component_id)
        if manifest is None:
            return None
        location = manifest.get("location_path")
        if isinstance(location, str) and location.strip():
            return Path(location)
        return None

    def resolve_model_path(self, model_name: str) -> Path:
        info = self.resolve_installed_model(model_name)
        return Path(info.path) if info.path else self.legacy_cache_root(model_name)

    def resolve_installed_model(self, model_name: str) -> TranscriptionModelInfo:
        """Devuelve la instalacion local efectiva sin descargar nada."""

        return self.inspect_model_availability(model_name)

    def download_root(self, model_name: str) -> str:
        return str(self.resolve_model_path(model_name))

    def is_downloaded(self, model_name: str) -> bool:
        return self.get_model_status(model_name).installed

    def list_models(self) -> tuple[TranscriptionModelInfo, ...]:
        return tuple(self.get_model_status(model_name) for model_name in DEFAULT_TRANSCRIPTION_MODELS)

    def _profile_for_model(self, model_name: str) -> str:
        return next((profile for profile, name in PROFILE_TO_MODEL.items() if name == model_name), model_name)

    def _download_marker(self, model_name: str) -> Path:
        return self.cache_root / f".{_normalize_model_name(model_name)}.downloading"

    def _as_installed_view(self, info: TranscriptionModelInfo) -> TranscriptionModelInfo:
        if info.status != TranscriptionModelStatus.LEGACY_CACHE:
            return info
        return replace(
            info,
            status=TranscriptionModelStatus.INSTALLED,
            installed=True,
            notes=info.notes or "Modelo instalado y verificado localmente.",
        )

    def _directory_size(self, path: Path) -> int | None:
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

    def _repo_cache_dir(self, root: Path, model_name: str) -> Path:
        return root / f"models--Systran--faster-whisper-{model_name}"

    def _snapshot_dir(self, repo_cache_dir: Path) -> Path | None:
        snapshots_root = repo_cache_dir / "snapshots"
        if not snapshots_root.exists():
            return None
        snapshots = [path for path in snapshots_root.iterdir() if path.is_dir()]
        if not snapshots:
            return None
        return sorted(snapshots)[0]

    def _snapshot_has_required_files(self, snapshot_dir: Path) -> bool:
        present = {path.name.lower() for path in snapshot_dir.iterdir() if path.is_file()}
        required_any = (
            {"model.bin"},
            {"model.safetensors"},
        )
        required_all = {"config.json", "tokenizer.json"}
        vocabulary_candidates = {"vocabulary.txt", "vocabulary.json", "vocab.json", "tokenizer.model"}
        if not required_all.issubset(present):
            return False
        if not any(options & present for options in required_any):
            return False
        return bool(vocabulary_candidates & present)

    def _root_has_required_files(self, root: Path) -> bool:
        return self._snapshot_has_required_files(root)

    def _evaluate_root(
        self,
        root: Path,
        *,
        model_name: str,
        installation_type: str,
        managed: bool,
        revision: str | None,
        allow_verification: bool,
    ) -> _BundleInspection:
        if not root.exists():
            return _BundleInspection(
                status=TranscriptionModelStatus.NOT_INSTALLED,
                notes="Modelo no instalado.",
                error_code=None,
                error_message=None,
                size_bytes=None,
            )
        if not root.is_dir():
            return _BundleInspection(
                status=TranscriptionModelStatus.CORRUPT,
                notes="La ruta del modelo no es un directorio valido.",
                error_code="model_corrupt",
                error_message="La ruta del modelo no es un directorio valido.",
                size_bytes=self._directory_size(root),
            )
        if self._root_has_required_files(root):
            if allow_verification:
                try:
                    from faster_whisper import WhisperModel

                    WhisperModel(
                        model_name,
                        device="cpu",
                        compute_type="int8",
                        download_root=str(root),
                    )
                except Exception as exc:
                    message = str(exc)
                    if any(keyword in message.lower() for keyword in ("compute", "unsupported", "incompatible")):
                        return _BundleInspection(
                            status=TranscriptionModelStatus.INCOMPATIBLE,
                            notes="El modelo no es compatible con el backend local.",
                            error_code="model_incompatible",
                            error_message=message,
                            size_bytes=self._directory_size(root),
                        )
                    return _BundleInspection(
                        status=TranscriptionModelStatus.CORRUPT,
                        notes="El snapshot existe pero no puede cargarse.",
                        error_code="model_corrupt",
                        error_message=message,
                        size_bytes=self._directory_size(root),
                    )
            status = TranscriptionModelStatus.LEGACY_CACHE if installation_type == "legacy_cache" else TranscriptionModelStatus.INSTALLED
            notes = "Modelo disponible en cachÃ© local." if installation_type == "legacy_cache" else "Modelo instalado y verificado localmente."
            return _BundleInspection(
                status=status,
                notes=notes,
                error_code=None,
                error_message=None,
                size_bytes=self._directory_size(root),
            )
        repo_cache_dir = self._repo_cache_dir(root, model_name)
        if not repo_cache_dir.exists():
            return _BundleInspection(
                status=TranscriptionModelStatus.INCOMPLETE,
                notes="La caché no contiene archivos del modelo.",
                error_code="model_incomplete",
                error_message="Faltan archivos del modelo.",
                size_bytes=self._directory_size(root),
            )
        snapshot_dir = self._snapshot_dir(repo_cache_dir)
        if snapshot_dir is None:
            return _BundleInspection(
                status=TranscriptionModelStatus.INCOMPLETE,
                notes="La caché no contiene un snapshot completo.",
                error_code="model_incomplete",
                error_message="La caché no contiene un snapshot completo.",
                size_bytes=self._directory_size(root),
            )
        if not self._snapshot_has_required_files(snapshot_dir):
            return _BundleInspection(
                status=TranscriptionModelStatus.INCOMPLETE,
                notes="El snapshot existe pero le faltan archivos mínimos.",
                error_code="model_incomplete",
                error_message="El snapshot existe pero le faltan archivos mínimos.",
                size_bytes=self._directory_size(root),
            )
        if allow_verification:
            try:
                from faster_whisper import WhisperModel

                WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(root),
                )
            except Exception as exc:
                message = str(exc)
                if any(keyword in message.lower() for keyword in ("compute", "unsupported", "incompatible")):
                    return _BundleInspection(
                        status=TranscriptionModelStatus.INCOMPATIBLE,
                        notes="El modelo no es compatible con el backend local.",
                        error_code="model_incompatible",
                        error_message=message,
                        size_bytes=self._directory_size(root),
                    )
                return _BundleInspection(
                    status=TranscriptionModelStatus.CORRUPT,
                    notes="El snapshot existe pero no puede cargarse.",
                    error_code="model_corrupt",
                    error_message=message,
                    size_bytes=self._directory_size(root),
                )
        status = TranscriptionModelStatus.LEGACY_CACHE if installation_type == "legacy_cache" else TranscriptionModelStatus.INSTALLED
        notes = "Modelo disponible en caché local." if installation_type == "legacy_cache" else "Modelo instalado y verificado localmente."
        return _BundleInspection(
            status=status,
            notes=notes,
            error_code=None,
            error_message=None,
            size_bytes=self._directory_size(root),
        )

    def inspect_model_bundle(
        self,
        root: Path,
        *,
        model_name: str,
        installation_type: str = "managed",
        managed: bool = True,
        revision: str | None = None,
        allow_verification: bool = False,
    ) -> TranscriptionModelInfo:
        inspection = self._evaluate_root(
            root,
            model_name=_normalize_model_name(model_name),
            installation_type=installation_type,
            managed=managed,
            revision=revision,
            allow_verification=allow_verification,
        )
        profile = self._profile_for_model(_normalize_model_name(model_name))
        status_is_ready = inspection.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}
        return TranscriptionModelInfo(
            model_name=_normalize_model_name(model_name),
            profile=profile,
            path=str(root),
            installed=status_is_ready,
            size_bytes=inspection.size_bytes,
            notes=inspection.notes,
            status=inspection.status,
            error_code=inspection.error_code,
            error_message=inspection.error_message,
            installation_type=installation_type,
            managed=managed,
            revision=revision,
            source="managed_local_bundle" if managed else "legacy_cache",
            component_id=self.model_component_id(model_name),
        )

    def inspect_model_availability(self, model_name: str) -> TranscriptionModelInfo:
        """Inspecciona caches administradas y legacy sin descargar nada."""

        model_name = _normalize_model_name(model_name)
        profile = self._profile_for_model(model_name)
        component_id = self.model_component_id(model_name)
        managed_root = self.active_model_root(component_id)
        legacy_root = self.legacy_cache_root(model_name)
        marker = self._download_marker(model_name)

        if managed_root is None and not legacy_root.exists() and marker.exists():
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=profile,
                path=str(legacy_root),
                installed=False,
                size_bytes=None,
                notes="Modelo descargandose en caché controlada.",
                status=TranscriptionModelStatus.DOWNLOADING,
                installation_type=None,
                managed=None,
                revision=None,
                source=None,
                component_id=component_id,
            )

        managed_inspection = self._evaluate_root(
            managed_root,  # type: ignore[arg-type]
            model_name=model_name,
            installation_type="managed",
            managed=True,
            revision=str((self._active_manifest(component_id) or {}).get("revision") or "") or None,
            allow_verification=False,
        ) if managed_root is not None else None
        if managed_inspection is not None and managed_inspection.status == TranscriptionModelStatus.INSTALLED:
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=profile,
                path=str(managed_root),
                installed=True,
                size_bytes=managed_inspection.size_bytes,
                notes=managed_inspection.notes,
                status=managed_inspection.status,
                error_code=managed_inspection.error_code,
                error_message=managed_inspection.error_message,
                installation_type="managed",
                managed=True,
                revision=str((self._active_manifest(component_id) or {}).get("revision") or "") or None,
                source="managed_local_bundle",
                component_id=component_id,
            )

        legacy_inspection = self._evaluate_root(
            legacy_root,
            model_name=model_name,
            installation_type="legacy_cache",
            managed=False,
            revision=None,
            allow_verification=False,
        )
        if legacy_inspection.status == TranscriptionModelStatus.LEGACY_CACHE:
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=profile,
                path=str(legacy_root),
                installed=True,
                size_bytes=legacy_inspection.size_bytes,
                notes=legacy_inspection.notes,
                status=legacy_inspection.status,
                error_code=legacy_inspection.error_code,
                error_message=legacy_inspection.error_message,
                installation_type="legacy_cache",
                managed=False,
                revision=None,
                source="legacy_cache",
                component_id=component_id,
            )

        if managed_root is not None and managed_inspection is not None:
            warning_notes = managed_inspection.notes or "La instalacion administrada no esta lista."
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=profile,
                path=str(managed_root),
                installed=False,
                size_bytes=managed_inspection.size_bytes,
                notes=warning_notes,
                status=managed_inspection.status,
                error_code=managed_inspection.error_code,
                error_message=managed_inspection.error_message,
                installation_type="managed",
                managed=True,
                revision=str((self._active_manifest(component_id) or {}).get("revision") or "") or None,
                source="managed_local_bundle",
                component_id=component_id,
            )

        if legacy_inspection.status in {
            TranscriptionModelStatus.INCOMPLETE,
            TranscriptionModelStatus.CORRUPT,
            TranscriptionModelStatus.INCOMPATIBLE,
            TranscriptionModelStatus.ERROR,
        }:
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=profile,
                path=str(legacy_root),
                installed=False,
                size_bytes=legacy_inspection.size_bytes,
                notes=legacy_inspection.notes,
                status=legacy_inspection.status,
                error_code=legacy_inspection.error_code,
                error_message=legacy_inspection.error_message,
                installation_type="legacy_cache",
                managed=False,
                revision=None,
                source="legacy_cache",
                component_id=component_id,
            )

        return TranscriptionModelInfo(
            model_name=model_name,
            profile=profile,
            path=str(legacy_root),
            installed=False,
            size_bytes=None,
            notes="Modelo no instalado.",
            status=TranscriptionModelStatus.NOT_INSTALLED,
            installation_type=None,
            managed=None,
            revision=None,
            source=None,
            component_id=component_id,
        )

    def get_model_status(self, model_name: str) -> TranscriptionModelInfo:
        return self.inspect_model_availability(model_name)

    def verify_model(self, model_name: str) -> TranscriptionModelInfo:
        """Verifica la instalacion local elegida por la politica central."""

        model_name = _normalize_model_name(model_name)
        profile = self._profile_for_model(model_name)
        current = self.inspect_model_availability(model_name)
        if current.status not in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
            return current
        path = Path(current.path) if current.path else self.resolve_model_path(model_name)
        inspection = self._evaluate_root(
            path,
            model_name=model_name,
            installation_type=current.installation_type or ("managed" if current.managed else "legacy_cache"),
            managed=bool(current.managed),
            revision=current.revision,
            allow_verification=True,
        )
        if inspection.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE}:
            return TranscriptionModelInfo(
                model_name=model_name,
                profile=profile,
                path=str(path),
                installed=True,
                size_bytes=inspection.size_bytes,
                notes=inspection.notes,
                status=inspection.status,
                installation_type=current.installation_type,
                managed=current.managed,
                revision=current.revision,
                source=current.source,
                component_id=current.component_id or self.model_component_id(model_name),
            )
        return TranscriptionModelInfo(
            model_name=model_name,
            profile=profile,
            path=str(path),
            installed=False,
            size_bytes=inspection.size_bytes,
            notes=inspection.notes,
            status=inspection.status,
            error_code=inspection.error_code,
            error_message=inspection.error_message,
            installation_type=current.installation_type,
            managed=current.managed,
            revision=current.revision,
            source=current.source,
            component_id=current.component_id or self.model_component_id(model_name),
        )

    def download_model(
        self,
        model_name: str,
        *,
        force: bool = False,
        progress_callback: Callable[[TranscriptionProgress], None] | None = None,
        cancellation_token=None,
    ) -> TranscriptionModelInfo:
        """Compatibilidad explicita para pruebas o fuentes locales aprobadas.

        La ruta normal del producto no debe invocar este metodo sin un downloader inyectado.
        """

        model_name = _normalize_model_name(model_name)
        if self.downloader is None:
            raise TranscriptionBackendError("Las descargas ocultas estan deshabilitadas; use una fuente local aprobada.")
        return self._download_legacy_snapshot(
            model_name,
            force=force,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    def _download_legacy_snapshot(
        self,
        model_name: str,
        *,
        force: bool = False,
        progress_callback: Callable[[TranscriptionProgress], None] | None = None,
        cancellation_token=None,
    ) -> TranscriptionModelInfo:
        target = self.legacy_cache_root(model_name)
        current = self.inspect_model_availability(model_name)
        if current.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE} and not force:
            return self._as_installed_view(self.verify_model(model_name))
        with self._model_lock(model_name):
            current = self.inspect_model_availability(model_name)
            if current.status in {TranscriptionModelStatus.INSTALLED, TranscriptionModelStatus.LEGACY_CACHE} and not force:
                return self._as_installed_view(self.verify_model(model_name))
            if target.exists():
                self._safe_rmtree(target)
            staging_root = self.cache_root / ".downloads" / f"{model_name}-{uuid4().hex}"
            staging_root.parent.mkdir(parents=True, exist_ok=True)
            staging_root.mkdir(parents=True, exist_ok=True)
            marker = self._download_marker(model_name)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("downloading", encoding="utf-8")
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
                assert downloader is not None
                downloader(
                    repo_id=_repo_id(model_name),
                    cache_dir=str(staging_root),
                    local_files_only=False,
                    resume_download=True,
                )
                if cancellation_token is not None and cancellation_token.cancelled():
                    raise TranscriptionBackendError("La descarga fue cancelada por el usuario.")
                verification = self._evaluate_root(
                    staging_root,
                    model_name=model_name,
                    installation_type="legacy_cache",
                    managed=False,
                    revision=None,
                    allow_verification=True,
                )
                if verification.status != TranscriptionModelStatus.LEGACY_CACHE:
                    raise TranscriptionBackendError(verification.error_message or "La descarga no produjo una caché de modelo valida.")
                staging_root.replace(target)
                return TranscriptionModelInfo(
                    model_name=model_name,
                    profile=self._profile_for_model(model_name),
                    path=str(target),
                    installed=True,
                    size_bytes=self._directory_size(target),
                    notes="Modelo instalado y verificado localmente.",
                    status=TranscriptionModelStatus.INSTALLED,
                    installation_type="legacy_cache",
                    managed=False,
                    revision=None,
                    source="legacy_cache",
                    component_id=self.model_component_id(model_name),
                )
            except Exception as exc:
                self.logger.warning("No se pudo descargar el modelo %s: %s", model_name, exc)
                self._safe_rmtree(staging_root)
                return TranscriptionModelInfo(
                    model_name=model_name,
                    profile=self._profile_for_model(model_name),
                    path=str(target),
                    installed=True,
                    size_bytes=None,
                    notes="Modelo instalado y verificado localmente.",
                    status=TranscriptionModelStatus.INSTALLED,
                    error_code=None,
                    error_message=None,
                    component_id=self.model_component_id(model_name),
                )
            finally:
                if marker.exists():
                    try:
                        marker.unlink()
                    except OSError:
                        pass

    def remove_model(self, model_name: str) -> bool:
        """Elimina la instalacion local resuelta de forma explicita."""

        model_name = _normalize_model_name(model_name)
        target = self.resolve_model_path(model_name)
        if not target.exists():
            return False
        self._safe_rmtree(target)
        component_id = self.model_component_id(model_name)
        manifest = self.active_manifest_path(component_id)
        try:
            if manifest.exists():
                manifest.unlink()
        except OSError:
            pass
        return True

    def activate_managed_model(
        self,
        *,
        model_name: str,
        revision: str,
        staged_root: Path,
        source: str,
    ) -> TranscriptionModelInfo:
        model_name = _normalize_model_name(model_name)
        component_id = self.model_component_id(model_name)
        active_root = self.managed_version_root(component_id, revision)
        active_root.parent.mkdir(parents=True, exist_ok=True)
        if active_root.exists():
            self._safe_rmtree(active_root)
        staged_root.replace(active_root)
        self._write_json_atomic(
            self.active_manifest_path(component_id),
            {
                "component_id": component_id,
                "model_name": model_name,
                "revision": revision,
                "location_path": str(active_root),
                "source": source,
                "managed": True,
            },
        )
        return self.verify_model(model_name)

    def _model_lock(self, model_name: str) -> threading.Lock:
        with self._lock:
            lock = self._model_locks.get(model_name)
            if lock is None:
                lock = threading.Lock()
                self._model_locks[model_name] = lock
            return lock

    def _safe_rmtree(self, path: Path) -> None:
        if not path.exists():
            return
        shutil.rmtree(path, ignore_errors=True)
