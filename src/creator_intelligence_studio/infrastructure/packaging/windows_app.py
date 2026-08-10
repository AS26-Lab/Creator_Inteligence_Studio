"""Windows application bundle metadata and layout helpers."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from creator_intelligence_studio._metadata import APP_NAME, VERSION

WINDOWS_APP_BUNDLE_NAME = "CreatorIntelligenceStudio"
WINDOWS_RUNTIME_MANIFEST_FILENAME = "runtime_manifest.json"
WINDOWS_RUNTIME_MANIFEST_FORMAT_VERSION = 1


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _normalize_architecture(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"amd64", "x64", "x86_64"}:
        return "x86_64"
    return normalized


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except Exception:
        return None


def _git_revision() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    revision = completed.stdout.strip()
    return revision or None


def _package_supports_gpu() -> bool:
    return all(
        _package_version(package) is not None
        for package in (
            "nvidia-cublas-cu12",
            "nvidia-cuda-runtime-cu12",
            "nvidia-cuda-nvrtc-cu12",
            "nvidia-cudnn-cu12",
        )
    )


@dataclass(frozen=True, slots=True)
class WindowsAppRuntimeManifest:
    """Deterministic metadata for a Windows application bundle."""

    runtime_format_version: int
    application_name: str
    application_version: str
    creator_intelligence_studio_version: str
    packaging_tool: str | None
    packaging_tool_version: str | None
    python_version: str
    faster_whisper_version: str | None
    ctranslate2_version: str | None
    platform: str
    architecture: str | None
    cpu_supported: bool
    gpu_supported: bool
    build_revision: str | None
    build_timestamp: str
    bundle_kind: str
    notices_reference: str | None = None
    source_kind: str = "application_bundled"
    runtime_root: str | None = None
    libraries_root: str | None = None
    resources_root: str | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WindowsAppRuntimeManifest":
        notes = payload.get("notes") or ()
        if isinstance(notes, list):
            notes = tuple(str(item) for item in notes)
        elif not isinstance(notes, tuple):
            notes = tuple(str(item) for item in notes) if notes else ()
        return cls(
            runtime_format_version=int(payload["runtime_format_version"]),
            application_name=str(payload["application_name"]),
            application_version=str(payload["application_version"]),
            creator_intelligence_studio_version=str(payload["creator_intelligence_studio_version"]),
            packaging_tool=payload.get("packaging_tool"),
            packaging_tool_version=payload.get("packaging_tool_version"),
            python_version=str(payload["python_version"]),
            faster_whisper_version=payload.get("faster_whisper_version"),
            ctranslate2_version=payload.get("ctranslate2_version"),
            platform=str(payload["platform"]),
            architecture=payload.get("architecture"),
            cpu_supported=bool(payload["cpu_supported"]),
            gpu_supported=bool(payload["gpu_supported"]),
            build_revision=payload.get("build_revision"),
            build_timestamp=str(payload["build_timestamp"]),
            bundle_kind=str(payload["bundle_kind"]),
            notices_reference=payload.get("notices_reference"),
            source_kind=str(payload.get("source_kind") or "application_bundled"),
            runtime_root=payload.get("runtime_root"),
            libraries_root=payload.get("libraries_root"),
            resources_root=payload.get("resources_root"),
            notes=tuple(str(item) for item in notes),
        )


def resolve_windows_app_bundle_root(*, executable: Path | None = None) -> Path:
    """Resolve the application bundle root for a frozen Windows build."""

    binary = Path(executable or getattr(sys, "executable", Path.cwd())).resolve()
    return binary.parent


def resolve_windows_runtime_manifest_path(bundle_root: Path) -> Path:
    """Return the canonical runtime manifest path inside a bundle."""

    return bundle_root / "runtime" / WINDOWS_RUNTIME_MANIFEST_FILENAME


def build_windows_runtime_manifest(
    *,
    bundle_root: Path | None = None,
    packaging_tool: str | None = None,
    packaging_tool_version: str | None = None,
    notices_reference: str | None = None,
    build_revision: str | None = None,
    bundle_kind: str = "onedir",
    python_version: str | None = None,
    faster_whisper_version: str | None = None,
    ctranslate2_version: str | None = None,
) -> WindowsAppRuntimeManifest:
    """Build a deterministic manifest for a packaged Windows build."""

    python_version = python_version or platform.python_version()
    faster_whisper_version = faster_whisper_version or _package_version("faster-whisper")
    ctranslate2_version = ctranslate2_version or _package_version("ctranslate2")
    architecture = _normalize_architecture(platform.machine())
    bundle_root = bundle_root.resolve() if bundle_root is not None else None
    runtime_root = str(bundle_root / "runtime") if bundle_root is not None else None
    libraries_root = str(bundle_root / "libraries") if bundle_root is not None else None
    resources_root = str(bundle_root / "resources") if bundle_root is not None else None
    return WindowsAppRuntimeManifest(
        runtime_format_version=WINDOWS_RUNTIME_MANIFEST_FORMAT_VERSION,
        application_name=APP_NAME,
        application_version=VERSION,
        creator_intelligence_studio_version=VERSION,
        packaging_tool=packaging_tool,
        packaging_tool_version=packaging_tool_version,
        python_version=python_version,
        faster_whisper_version=faster_whisper_version,
        ctranslate2_version=ctranslate2_version,
        platform=platform.system() or "Windows",
        architecture=architecture,
        cpu_supported=bool(faster_whisper_version and ctranslate2_version),
        gpu_supported=_package_supports_gpu(),
        build_revision=build_revision or _git_revision(),
        build_timestamp=_utc_now(),
        bundle_kind=bundle_kind,
        notices_reference=notices_reference,
        runtime_root=runtime_root,
        libraries_root=libraries_root,
        resources_root=resources_root,
        notes=(),
    )


def write_windows_runtime_manifest(bundle_root: Path, manifest: WindowsAppRuntimeManifest) -> Path:
    """Persist the runtime manifest into the bundle layout."""

    path = resolve_windows_runtime_manifest_path(bundle_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.to_json(), encoding="utf-8")
    return path


def load_windows_runtime_manifest(bundle_root: Path) -> WindowsAppRuntimeManifest | None:
    """Load the runtime manifest if the bundle provides one."""

    path = resolve_windows_runtime_manifest_path(bundle_root)
    if not path.exists():
        legacy_path = bundle_root / WINDOWS_RUNTIME_MANIFEST_FILENAME
        if not legacy_path.exists():
            return None
        path = legacy_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return WindowsAppRuntimeManifest.from_dict(payload)
