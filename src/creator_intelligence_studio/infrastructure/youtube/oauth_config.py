"""Helpers for resolving the public YouTube OAuth application identity."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class YouTubeOAuthClientBootstrap:
    client_id: str
    client_secret: str | None = None
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
    client_secret = str(client_block.get("client_secret") or payload.get("client_secret") or "").strip() or None
    client_secret_present = bool(client_secret)
    return YouTubeOAuthClientBootstrap(
        client_id=client_id,
        client_secret=client_secret,
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


def resolve_youtube_oauth_client_secret(*, configured_client_secret: str | None, developer_json_path: Path | None = None) -> str | None:
    if configured_client_secret is not None:
        client_secret = configured_client_secret.strip()
        if client_secret:
            return client_secret
    if developer_json_path is None:
        return None
    bootstrap = load_google_desktop_client_bootstrap(developer_json_path)
    if bootstrap.client_secret:
        return bootstrap.client_secret
    return None


def resolve_youtube_oauth_app_config(path: Path | None = None) -> tuple[str | None, str | None]:
    if path is None:
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, None
    except Exception:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    client_id = str(payload.get("youtube_oauth_client_id") or "").strip() or None
    client_secret = str(payload.get("youtube_oauth_client_secret") or "").strip() or None
    return client_id, client_secret


def build_youtube_credential_reference(*, creator_id: str, google_account_identifier: str | None) -> str:
    normalized_identifier = (google_account_identifier or "pending").strip().casefold()
    digest = hashlib.sha256(f"{creator_id}:youtube:{normalized_identifier}".encode("utf-8")).hexdigest()[:16]
    return f"youtube_{creator_id}_{digest}"
