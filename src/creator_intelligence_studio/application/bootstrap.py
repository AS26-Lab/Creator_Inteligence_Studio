"""Bootstrap minimo de la aplicacion."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from creator_intelligence_studio import APP_NAME, VERSION
from creator_intelligence_studio.infrastructure.configuration.settings import (
    AppSettings,
    SettingsError,
    load_settings,
)
from creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic import (
    collect_environment_diagnostic,
)
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    EnvironmentDiagnostic,
)
from creator_intelligence_studio.infrastructure.logging.logging_setup import (
    setup_logging,
)
from creator_intelligence_studio.shared.paths import ProjectPaths, discover_project_root


@dataclass(frozen=True)
class BootstrapContext:
    """Contexto preparado por el bootstrap."""

    settings: AppSettings
    paths: ProjectPaths
    diagnostic: EnvironmentDiagnostic


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="creator_intelligence_studio",
        description="Arranque minimo de Creator Intelligence Studio.",
    )
    parser.add_argument(
        "--diagnostic-json",
        action="store_true",
        help="Imprime el diagnostico en formato JSON valido.",
    )
    return parser.parse_args(argv)


def _load_context() -> BootstrapContext:
    project_root = discover_project_root()
    settings = load_settings(project_root / "config" / "default.json")
    paths = ProjectPaths.from_settings(project_root, settings)
    paths.ensure_runtime_directories()
    logger = setup_logging(settings=settings, paths=paths)
    logger.info("Inicializacion del entorno completada.")
    diagnostic = collect_environment_diagnostic(
        settings=settings,
        paths=paths,
    )
    return BootstrapContext(settings=settings, paths=paths, diagnostic=diagnostic)


def _print_summary(context: BootstrapContext, stream) -> None:
    diagnostic = context.diagnostic
    print(f"{APP_NAME} v{VERSION}", file=stream)
    print(f"Entorno: {context.settings.environment}", file=stream)
    print(f"Ruta del proyecto: {context.paths.project_root}", file=stream)
    print(f"Python: {diagnostic.python_version} ({diagnostic.python_executable})", file=stream)
    print(
        f"Backend preferido: {diagnostic.preferred_compute_backend}",
        file=stream,
    )
    print(
        "Modo basico disponible: "
        + ("si" if diagnostic.state.ready_for_basic_mode else "no"),
        file=stream,
    )
    print(
        "CUDA detectado por driver: "
        + ("si" if diagnostic.state.cuda_driver_detected else "no"),
        file=stream,
    )
    print(
        "CUDA verificado en runtime: "
        + ("si" if not diagnostic.state.cuda_runtime_not_verified else "no"),
        file=stream,
    )
    if diagnostic.gpu_devices:
        gpu = diagnostic.gpu_devices[0]
        memory = (
            f"{gpu.memory_total_mib} MiB"
            if gpu.memory_total_mib is not None
            else "no verificado"
        )
        print(f"GPU NVIDIA: {gpu.name} | VRAM: {memory}", file=stream)
    else:
        print("GPU NVIDIA: no verificado", file=stream)
    for warning in diagnostic.warnings:
        print(f"Advertencia: {warning}", file=stream)


def run(argv: Sequence[str] | None = (), stdout=None, stderr=None) -> int:
    """Ejecuta el bootstrap de la aplicacion."""

    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args = _parse_args(argv)

    try:
        context = _load_context()
    except SettingsError as exc:
        print(f"Error de configuracion: {exc}", file=stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado durante el arranque: {exc}", file=stderr)
        return 1

    diagnostic = context.diagnostic

    if args.diagnostic_json:
        print(diagnostic.to_json(), file=stdout)
    else:
        _print_summary(context, stdout)

    return 0 if diagnostic.state.ready_for_basic_mode else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada principal."""

    return run(argv=sys.argv[1:] if argv is None else argv)
