from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from creator_intelligence_studio.infrastructure.packaging import (  # noqa: E402
    WINDOWS_APP_BUNDLE_NAME,
    WINDOWS_RUNTIME_MANIFEST_FILENAME,
    build_windows_runtime_manifest,
    write_windows_runtime_manifest,
)


@dataclass(frozen=True, slots=True)
class WindowsAppBuildReport:
    project_root: str
    staging_root: str
    bundle_root: str
    manifest_path: str
    packaging_tool: str | None
    packaging_tool_version: str | None
    build_revision: str | None
    bundle_kind: str
    manifest: dict[str, Any]
    invoked_packager: bool
    success: bool
    blockers: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    output_paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


def _detect_pyinstaller() -> tuple[str | None, str | None]:
    try:
        import PyInstaller  # type: ignore

        return "PyInstaller", getattr(PyInstaller, "__version__", None)
    except Exception:
        return None, None


def _collect_output_paths(bundle_root: Path) -> tuple[str, ...]:
    paths = [
        bundle_root / f"{WINDOWS_APP_BUNDLE_NAME}.exe",
        bundle_root / "runtime" / WINDOWS_RUNTIME_MANIFEST_FILENAME,
        bundle_root / "config" / "default.json",
        bundle_root / "libraries",
        bundle_root / "resources",
    ]
    return tuple(str(path) for path in paths)


def _materialize_bundle_resource(bundle_root: Path, relative_path: str) -> None:
    internal_path = bundle_root / "_internal" / relative_path
    target_path = bundle_root / relative_path
    if not internal_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(internal_path, target_path)


def build_windows_app(
    *,
    project_root: Path | None = None,
    staging_root: Path | None = None,
    invoke_packager: bool = True,
) -> WindowsAppBuildReport:
    blockers: list[str] = []
    notes: list[str] = []
    if (platform.system() or "").strip().lower() != "windows":
        blockers.append("Este comando solo esta soportado en Windows.")
    project_root = (project_root or PROJECT_ROOT).resolve()
    staging_root = (staging_root or (project_root / "dist")).resolve()
    bundle_root = staging_root / WINDOWS_APP_BUNDLE_NAME
    packaging_tool, packaging_tool_version = _detect_pyinstaller()
    manifest = build_windows_runtime_manifest(
        bundle_root=bundle_root,
        packaging_tool=packaging_tool,
        packaging_tool_version=packaging_tool_version,
        notices_reference="docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
        build_revision=subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=project_root,
        ).stdout.strip() or None,
        bundle_kind="onedir",
    )
    manifest_path = bundle_root / "runtime" / WINDOWS_RUNTIME_MANIFEST_FILENAME
    invoked_packager = False
    success = True

    if manifest.faster_whisper_version is None or manifest.ctranslate2_version is None:
        blockers.append("No se pudieron determinar las versiones del runtime de transcripcion.")
        success = False
    if packaging_tool is None and invoke_packager:
        blockers.append("PyInstaller no esta instalado en el entorno de build.")
        success = False
    elif invoke_packager:
        invoked_packager = True
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name",
            WINDOWS_APP_BUNDLE_NAME,
            "--distpath",
            str(staging_root),
            "--workpath",
            str(project_root / "build"),
            "--specpath",
            str(project_root / "build"),
            "--paths",
            str(SRC_ROOT),
            "--collect-all",
            "PySide6",
            "--collect-all",
            "faster_whisper",
            "--collect-all",
            "ctranslate2",
            "--collect-all",
            "backports.tarfile",
            "--hidden-import",
            "backports",
            "--add-data",
            f"{project_root / 'config' / 'default.json'};config",
            "--add-data",
            f"{project_root / 'docs' / 'TRANSCRIPTION_RUNTIME_LICENSING.md'};docs",
            str(SRC_ROOT / "creator_intelligence_studio" / "__main__.py"),
        ]
        completed = subprocess.run(cmd, cwd=project_root, check=False)
        success = completed.returncode == 0
        if not success:
            blockers.append(f"PyInstaller devolvio el codigo {completed.returncode}.")
        else:
            _materialize_bundle_resource(bundle_root, "config/default.json")
            _materialize_bundle_resource(
                bundle_root,
                "docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
            )
            manifest_path = write_windows_runtime_manifest(bundle_root, manifest)
            if not manifest_path.exists():
                blockers.append("El runtime manifest no quedo materializado en el bundle.")
                success = False
            else:
                notes.append("Se materializo el runtime manifest en el bundle.")
            notes.append("Se invoco PyInstaller en modo onedir.")
    else:
        manifest_path = write_windows_runtime_manifest(bundle_root, manifest)
        if not manifest_path.exists():
            blockers.append("El runtime manifest no quedo materializado en el bundle.")
            success = False
        notes.append("Se omitio la ejecucion real del empaquetador.")

    return WindowsAppBuildReport(
        project_root=str(project_root),
        staging_root=str(staging_root),
        bundle_root=str(bundle_root),
        manifest_path=str(manifest_path),
        packaging_tool=packaging_tool,
        packaging_tool_version=packaging_tool_version,
        build_revision=manifest.build_revision,
        bundle_kind=manifest.bundle_kind,
        manifest=manifest.to_dict(),
        invoked_packager=invoked_packager,
        success=success,
        blockers=tuple(blockers),
        notes=tuple(notes),
        output_paths=_collect_output_paths(bundle_root),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Windows onedir application bundle.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--staging-root", default=None)
    parser.add_argument("--no-packager", action="store_true", help="Only write the runtime manifest and build plan.")
    parser.add_argument("--report-json", action="store_true", help="Print a JSON report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = build_windows_app(
        project_root=Path(args.project_root),
        staging_root=Path(args.staging_root) if args.staging_root else None,
        invoke_packager=not args.no_packager,
    )
    payload = report.to_json()
    if args.report_json:
        print(payload)
    else:
        print(payload)
    return 0 if report.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
