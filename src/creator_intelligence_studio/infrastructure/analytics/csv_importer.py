"""Importador CSV para analytics."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from .models import SourceTable


def _fingerprint_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def detect_csv_delimiter(sample_text: str) -> str:
    candidates = [",", ";", "\t"]
    scores = {delimiter: sample_text.count(delimiter) for delimiter in candidates}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ","


def load_csv_table(path: Path, *, max_bytes: int = 25_000_000, delimiter: str | None = None) -> SourceTable:
    raw = path.read_bytes()
    if not raw:
        return SourceTable(path, "csv", _fingerprint_bytes(raw), path.name, len(raw), delimiter=delimiter, errors=("empty_file",))
    if len(raw) > max_bytes:
        return SourceTable(path, "csv", _fingerprint_bytes(raw), path.name, len(raw), delimiter=delimiter, errors=("file_too_large",))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return SourceTable(path, "csv", _fingerprint_bytes(raw), path.name, len(raw), delimiter=delimiter, errors=("invalid_encoding",))
    sniffed = delimiter or detect_csv_delimiter(text[:8192])
    try:
        reader = csv.DictReader(text.splitlines(), delimiter=sniffed)
        headers = tuple(reader.fieldnames or [])
        rows = tuple({str(key): value for key, value in row.items()} for row in reader)
    except csv.Error as exc:
        return SourceTable(path, "csv", _fingerprint_bytes(raw), path.name, len(raw), delimiter=sniffed, errors=(str(exc),))
    return SourceTable(path, "csv", _fingerprint_bytes(raw), path.name, len(raw), delimiter=sniffed, headers=headers, rows=rows)
