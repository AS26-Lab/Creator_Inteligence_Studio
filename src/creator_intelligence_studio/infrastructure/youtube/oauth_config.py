"""Helpers for resolving the public YouTube OAuth application identity."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class YouTubeOAuthClientBootstrap:
    client_id: str
    client_secret_present: bool = False
    source_path: str | None = None
    source_kind: str = "configuration"

    def to_public_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "client_secret_present": self.client_secret_present,
            "source_path": self.source_path,
            "source_kind": self.source_kind,
        }


def load_google_desktop_client_bootstrap(path: Path) -> YouTubeOAuthClientBootstrap:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The Google OAuth client file must contain a JSON object.")
    client_block = payload.get("installed") if isinstance(payload.get("installed"), dict) else payload.get("web")
    if not isinstance(client_block, dict):
        client_block = payload
    client_id = str(client_block.get("client_id") or payload.get("client_id") or "").strip()
    if not client_id:
        raise ValueError("The Google OAuth client file does not contain a client_id.")
    client_secret_present = bool(str(client_block.get("client_secret") or payload.get("client_secret") or "").strip())
    return YouTubeOAuthClientBootstrap(
        client_id=client_id,
        client_secret_present=client_secret_present,
        source_path=str(path),
        source_kind="developer_json",
    )


def resolve_youtube_oauth_client_id(*, configured_client_id: str | None, developer_json_path: Path | None = None) -> str | None:
    if configured_client_id is not None:
        client_id = configured_client_id.strip()
        if client_id:
            return client_id
    if developer_json_path is None:
        return None
    bootstrap = load_google_desktop_client_bootstrap(developer_json_path)
    return bootstrap.client_id

