"""Repositorio filesystem para descargas persistidas."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterable

from creator_intelligence_studio.domain.components.downloads import ComponentDownloadRecord


class FileSystemComponentDownloadRepository:
    """Persistencia local segura basada en JSON por descarga."""

    def __init__(self, downloads_root: Path) -> None:
        self.downloads_root = downloads_root

    def ensure_root(self) -> None:
        self.downloads_root.mkdir(parents=True, exist_ok=True)

    def component_directory(self, component_id: str) -> Path:
        return self.downloads_root / component_id.strip().lower()

    def record_metadata_path(self, download_id: str, component_id: str) -> Path:
        return self.component_directory(component_id) / f"{download_id}.metadata.json"

    def record_partial_path(self, download_id: str, component_id: str) -> Path:
        return self.component_directory(component_id) / f"{download_id}.partial"

    def record_verified_path(self, download_id: str, component_id: str) -> Path:
        return self.component_directory(component_id) / f"{download_id}.verified"

    def record_exists(self, download_id: str, component_id: str) -> bool:
        return self.record_metadata_path(download_id, component_id).exists()

    def list_records(self) -> tuple[ComponentDownloadRecord, ...]:
        records: list[ComponentDownloadRecord] = []
        if not self.downloads_root.exists():
            return ()
        for metadata_file in sorted(self.downloads_root.glob("*/*.metadata.json")):
            record = self.load_record(metadata_file)
            if record is not None:
                records.append(record)
        return tuple(records)

    def load_record(self, metadata_file: Path) -> ComponentDownloadRecord | None:
        try:
            raw = metadata_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except Exception:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return ComponentDownloadRecord.from_dict(payload)

    def get_record(self, download_id: str) -> ComponentDownloadRecord | None:
        for record in self.list_records():
            if record.download_id == download_id:
                return record
        return None

    def find_by_identity(self, identity_key: str) -> ComponentDownloadRecord | None:
        normalized = identity_key.strip()
        for record in self.list_records():
            if record.identity_key == normalized:
                return record
        return None

    def save_record(self, record: ComponentDownloadRecord) -> ComponentDownloadRecord:
        self.ensure_root()
        component_dir = self.component_directory(record.component_id)
        component_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = self.record_metadata_path(record.download_id, record.component_id)
        temp_path = metadata_path.with_name(metadata_path.name + ".tmp")
        temp_path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        replaced = False
        try:
            for attempt in range(6):
                try:
                    os.replace(temp_path, metadata_path)
                    replaced = True
                    break
                except PermissionError:
                    if attempt >= 5:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            if not replaced:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass
        return record

    def delete_record(self, download_id: str) -> bool:
        removed = False
        for record in self.list_records():
            if record.download_id != download_id:
                continue
            metadata_path = self.record_metadata_path(record.download_id, record.component_id)
            try:
                metadata_path.unlink()
                removed = True
            except FileNotFoundError:
                pass
            break
        return removed

    def iter_paths_for_record(self, record: ComponentDownloadRecord) -> Iterable[Path]:
        yield Path(record.partial_path)
        yield Path(record.verified_artifact_path)
        yield self.record_metadata_path(record.download_id, record.component_id)
