"""Importador XLSX para analytics sin dependencias externas."""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import SourceTable


_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _fingerprint_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        return None


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = _read_xml(zf, "xl/sharedStrings.xml")
    if root is None:
        return []
    values: list[str] = []
    for si in root.findall("a:si", _NS):
        text_parts = [node.text or "" for node in si.iterfind(".//a:t", _NS)]
        values.append("".join(text_parts))
    return values


def _column_index(reference: str) -> int | None:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        return None
    result = 0
    for char in match.group(1):
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("a:v", _NS)
    if cell_type == "s" and value_node is not None and value_node.text is not None:
        try:
            return shared_strings[int(value_node.text)]
        except Exception:
            return value_node.text
    if cell_type == "inlineStr":
        text = cell.find(".//a:t", _NS)
        return text.text if text is not None and text.text is not None else ""
    if value_node is not None and value_node.text is not None:
        return value_node.text
    if cell.find("a:f", _NS) is not None and value_node is not None and value_node.text is not None:
        return value_node.text
    return ""


def _sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = _read_xml(zf, "xl/workbook.xml")
    rels = _read_xml(zf, "xl/_rels/workbook.xml.rels")
    if workbook is None or rels is None:
        return []
    rel_map = {
        rel.attrib.get("Id"): rel.attrib.get("Target", "")
        for rel in rels.findall("pr:Relationship", _NS)
    }
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall("a:sheets/a:sheet", _NS):
        rel_id = sheet.attrib.get(f"{{{_NS['r']}}}id")
        target = rel_map.get(rel_id, "")
        if target and not target.startswith("xl/"):
            target = f"xl/{target.lstrip('/')}"
        sheets.append((sheet.attrib.get("name", "Sheet1"), target))
    return sheets


def load_xlsx_table(path: Path, *, sheet_name: str | None = None, max_bytes: int = 25_000_000) -> SourceTable:
    raw = path.read_bytes()
    fingerprint = _fingerprint_bytes(raw)
    if not raw:
        return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=sheet_name, errors=("empty_file",))
    if len(raw) > max_bytes:
        return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=sheet_name, errors=("file_too_large",))
    if not zipfile.is_zipfile(path):
        return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=sheet_name, errors=("invalid_xlsx",))

    with zipfile.ZipFile(path) as zf:
        sheets = _sheet_targets(zf)
        if not sheets:
            return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=sheet_name, errors=("workbook_without_sheets",))
        selected_name, target = next((item for item in sheets if item[0] == sheet_name), sheets[0])
        if not target:
            return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=selected_name, errors=("sheet_not_found",))
        sheet = _read_xml(zf, target)
        if sheet is None:
            return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=selected_name, errors=("sheet_not_found",))

        shared_strings = _shared_strings(zf)
        sheet_rows = sheet.findall("a:sheetData/a:row", _NS)
        if not sheet_rows:
            return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=selected_name, errors=("missing_headers",))

        header_row = sheet_rows[0]
        headers: list[str] = []
        header_by_index: dict[int, str] = {}
        for cell in header_row.findall("a:c", _NS):
            idx = _column_index(cell.attrib.get("r", ""))
            if idx is None:
                continue
            header = _cell_value(cell, shared_strings).strip()
            if not header:
                continue
            headers.append(header)
            header_by_index[idx] = header
        if not headers:
            return SourceTable(path, "xlsx", fingerprint, path.name, len(raw), sheet_name=selected_name, errors=("missing_headers",))

        data_rows: list[dict[str, object]] = []
        for row in sheet_rows[1:]:
            row_values: dict[str, object] = {}
            for cell in row.findall("a:c", _NS):
                idx = _column_index(cell.attrib.get("r", ""))
                if idx is None:
                    continue
                header = header_by_index.get(idx)
                if header is None:
                    continue
                row_values[header] = _cell_value(cell, shared_strings)
            if any(str(value).strip() for value in row_values.values()):
                data_rows.append(row_values)

        return SourceTable(
            path=path,
            source_type="xlsx",
            source_fingerprint=fingerprint,
            source_filename=path.name,
            size_bytes=len(raw),
            sheet_name=selected_name,
            headers=tuple(headers),
            rows=tuple(data_rows),
        )
