"""Adaptador para archivos locales de referencia."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .source_adapter import MarketSourcePage


class FileSourceAdapter:
    source_type = "file"

    def is_available(self) -> bool:
        return True

    def search(self, query: dict[str, Any]) -> MarketSourcePage:
        file_path = query.get("file_path")
        if not file_path:
            return MarketSourcePage(items=())
        path = Path(str(file_path))
        if not path.exists():
            return MarketSourcePage(items=())
        payload = {"file_path": str(path), "content": path.read_text(encoding="utf-8", errors="replace")}
        return MarketSourcePage(items=(payload,), next_cursor=None, raw_json=None)

