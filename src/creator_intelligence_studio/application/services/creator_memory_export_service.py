"""Servicio fino de exportacion de memoria."""

from __future__ import annotations

from pathlib import Path

from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService


class CreatorMemoryExportService:
    def __init__(self, service: CreatorMemoryService) -> None:
        self.service = service

    def export_json(self, creator_id: str, *, summary_only: bool = False) -> str:
        return self.service.export_json(creator_id, summary_only=summary_only)

    def export_txt(self, creator_id: str) -> str:
        return self.service.export_txt(creator_id)

    def export_csv(self, creator_id: str, kind: str) -> str:
        return self.service.export_csv(creator_id, kind)

    def write_export(self, creator_id: str, kind: str, format_name: str, destination: Path | None = None) -> Path:
        destination = destination or (self.service.paths.data_directory / "creator_memory" / "exports")
        destination.mkdir(parents=True, exist_ok=True)
        stem = f"{creator_id}_{kind}_{format_name}"
        if format_name == "json":
            path = destination / f"{stem}.json"
            path.write_text(self.export_json(creator_id), encoding="utf-8")
            return path
        if format_name == "txt":
            path = destination / f"{stem}.txt"
            path.write_text(self.export_txt(creator_id), encoding="utf-8")
            return path
        if format_name == "csv":
            path = destination / f"{stem}.csv"
            path.write_text(self.export_csv(creator_id, kind), encoding="utf-8")
            return path
        raise ValueError("Formato no soportado.")

