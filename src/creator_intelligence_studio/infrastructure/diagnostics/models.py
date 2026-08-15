"""Modelos de diagnostico del entorno."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GpuInfo:
    """Informacion de una GPU detectada por nvidia-smi."""

    name: str
    driver_version: str | None
    memory_total_mib: int | None


@dataclass(frozen=True)
class DiagnosticState:
    """Estado general del diagnostico."""

    ready_for_basic_mode: bool
    cuda_driver_detected: bool
    cuda_runtime_not_verified: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnvironmentDiagnostic:
    """Resultado completo del diagnostico de entorno."""

    application_name: str
    application_version: str
    project_root: Path
    os_name: str
    os_version: str | None
    os_architecture: str | None
    python_version: str
    python_executable: str
    cpu_reported: str | None
    logical_processors: int | None
    nvidia_smi_available: bool
    gpu_devices: tuple[GpuInfo, ...] = ()
    nvidia_driver_version: str | None = None
    cuda_version_reported: str | None = None
    git_available: bool = False
    git_version: str | None = None
    free_space_bytes: int | None = None
    preferred_compute_backend: str = "cuda"
    ai_runtime_available: bool = False
    openai_configured: bool = False
    anthropic_configured: bool = False
    model_roles_configured: bool = False
    budget_policy_configured: bool = False
    credential_store_available: bool = False
    integration_contract_version: str | None = None
    registered_connector_count: int = 0
    registered_connector_ids: tuple[str, ...] = ()
    integration_connectors: tuple[dict[str, Any], ...] = ()
    packaged_application: bool = False
    application_root: str | None = None
    runtime_manifest_path: str | None = None
    runtime_manifest: dict[str, Any] | None = None
    state: DiagnosticState = field(
        default_factory=lambda: DiagnosticState(
            ready_for_basic_mode=True,
            cuda_driver_detected=False,
            cuda_runtime_not_verified=True,
        )
    )
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convierte el diagnostico a un diccionario serializable."""

        payload = asdict(self)
        payload["project_root"] = str(self.project_root)
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        """Serializa el diagnostico como JSON valido."""

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def summary_lines(self) -> list[str]:
        """Genera una vista resumida legible para consola."""

        lines = [
            f"Aplicacion: {self.application_name} {self.application_version}",
            f"Proyecto: {self.project_root}",
            f"Empaquetada: {'si' if self.packaged_application else 'no'}",
            f"Sistema operativo: {self.os_name} {self.os_version or 'no verificado'}",
            f"Arquitectura: {self.os_architecture or 'no verificado'}",
            f"Python: {self.python_version}",
            f"Ejecutable: {self.python_executable}",
            f"CPU: {self.cpu_reported or 'no verificado'}",
            f"Procesadores logicos: {self.logical_processors or 'no verificado'}",
            f"Git disponible: {'si' if self.git_available else 'no'}",
            f"nvidia-smi disponible: {'si' if self.nvidia_smi_available else 'no'}",
            f"Backend preferido: {self.preferred_compute_backend}",
            f"AI runtime disponible: {'si' if self.ai_runtime_available else 'no'}",
            f"OpenAI configurado: {'si' if self.openai_configured else 'no'}",
            f"Anthropic configurado: {'si' if self.anthropic_configured else 'no'}",
            f"Modelos por rol configurados: {'si' if self.model_roles_configured else 'no'}",
            f"Presupuesto AI configurado: {'si' if self.budget_policy_configured else 'no'}",
            f"Credential store disponible: {'si' if self.credential_store_available else 'no'}",
            f"Integraciones registradas: {self.registered_connector_count}",
            f"Modo basico listo: {'si' if self.state.ready_for_basic_mode else 'no'}",
        ]
        if self.integration_contract_version:
            lines.append(f"Integration contract: {self.integration_contract_version}")
        if self.registered_connector_ids:
            lines.append(f"Connector IDs: {', '.join(self.registered_connector_ids)}")
        if self.gpu_devices:
            gpu = self.gpu_devices[0]
            lines.append(
                "GPU NVIDIA: "
                f"{gpu.name} | driver {gpu.driver_version or 'no verificado'} | "
                f"VRAM {gpu.memory_total_mib if gpu.memory_total_mib is not None else 'no verificado'} MiB"
            )
        else:
            lines.append("GPU NVIDIA: no verificado")
        if self.cuda_version_reported:
            lines.append(f"CUDA reportada por driver: {self.cuda_version_reported}")
        if self.free_space_bytes is not None:
            lines.append(f"Espacio libre en la unidad del proyecto: {self.free_space_bytes} bytes")
        if self.runtime_manifest_path:
            lines.append(f"Runtime manifest: {self.runtime_manifest_path}")
        if self.errors:
            lines.append("Errores:")
            lines.extend(f"- {error}" for error in self.errors)
        if self.warnings:
            lines.append("Advertencias:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        return lines

    def __str__(self) -> str:
        return "\n".join(self.summary_lines())
