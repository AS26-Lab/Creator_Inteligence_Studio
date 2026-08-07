"""Utilidades seguras para copiar o extraer bundles locales controlados."""

from __future__ import annotations

import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_MEMBERS = 512
MAX_ARCHIVE_EXTRACTED_BYTES = 512 * 1024 * 1024


def _safe_resolve(path: Path) -> Path:
    return path.resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        return _safe_resolve(path).is_relative_to(_safe_resolve(root))
    except Exception:
        return False


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Symlink no permitido: {path}")


def copy_directory_tree(source: Path, destination: Path) -> None:
    """Copia un arbol local sin seguir symlinks."""

    if not source.exists() or not source.is_dir():
        raise ValueError(f"El origen no es un directorio valido: {source}")
    _reject_symlink(source)
    destination.mkdir(parents=True, exist_ok=False)
    for current_root, dirnames, filenames in os.walk(source):
        current_root_path = Path(current_root)
        _reject_symlink(current_root_path)
        relative_root = current_root_path.relative_to(source)
        target_root = destination / relative_root
        target_root.mkdir(parents=True, exist_ok=True)
        for dirname in list(dirnames):
            source_dir = current_root_path / dirname
            _reject_symlink(source_dir)
        for filename in filenames:
            source_file = current_root_path / filename
            _reject_symlink(source_file)
            target_file = target_root / filename
            shutil.copy2(source_file, target_file)


def safe_extract_zip(source: Path, destination: Path) -> int:
    """Extrae un ZIP bloqueando traversal y links peligrosos."""

    if not zipfile.is_zipfile(source):
        raise ValueError(f"El archivo no es un ZIP valido: {source}")
    extracted_size = 0
    seen_paths: set[str] = set()
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("El archivo contiene demasiados elementos.")
        for member in members:
            if member.is_dir():
                continue
            member_name = member.filename.replace("\\", "/")
            pure = PurePosixPath(member_name)
            if pure.is_absolute() or member_name.startswith("/") or re.match(r"^[a-zA-Z]:", member_name):
                raise ValueError(f"Ruta absoluta no permitida: {member.filename}")
            if ".." in pure.parts:
                raise ValueError(f"Traversal no permitido: {member.filename}")
            normalized = str(pure)
            if normalized in seen_paths:
                raise ValueError(f"Nombre duplicado conflictivo: {member.filename}")
            seen_paths.add(normalized)
            if member.file_size < 0:
                raise ValueError(f"Tamano invalido: {member.filename}")
            extracted_size += int(member.file_size)
            if extracted_size > MAX_ARCHIVE_EXTRACTED_BYTES:
                raise ValueError("El archivo excede el tamano maximo permitido.")
            external_attr = member.external_attr >> 16
            if external_attr and stat.S_ISLNK(external_attr):
                raise ValueError(f"Symlink no permitido: {member.filename}")
            target_path = _safe_resolve(destination / pure)
            if not _is_within(target_path, destination):
                raise ValueError(f"Extraccion fuera del staging: {member.filename}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return extracted_size

