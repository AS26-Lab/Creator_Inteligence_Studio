"""Almacenamiento local de credenciales para TikTok."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TikTokCredentialBundle:
    client_id: str | None
    access_token: str | None
    refresh_token: str | None
    token_type: str | None
    expires_at: str | None
    refresh_expires_at: str | None
    granted_scopes: tuple[str, ...]
    open_id: str | None
    union_id: str | None
    account_identifier: str | None
    provider: str

    def to_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "refresh_expires_at": self.refresh_expires_at,
            "granted_scopes": list(self.granted_scopes),
            "open_id": self.open_id,
            "union_id": self.union_id,
            "account_identifier": self.account_identifier,
            "provider": self.provider,
        }


class TikTokCredentialStore(Protocol):
    def save(self, reference: str, bundle: TikTokCredentialBundle) -> None: ...
    def load(self, reference: str) -> TikTokCredentialBundle | None: ...
    def delete(self, reference: str) -> None: ...


def _derive_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 120_000, dklen=32)


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


class DevelopmentTikTokCredentialStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, reference: str) -> Path:
        return self._root / f"{reference}.json"

    def save(self, reference: str, bundle: TikTokCredentialBundle) -> None:
        self._path(reference).write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, reference: str) -> TikTokCredentialBundle | None:
        path = self._path(reference)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TikTokCredentialBundle(
            client_id=payload.get("client_id"),
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type"),
            expires_at=payload.get("expires_at"),
            refresh_expires_at=payload.get("refresh_expires_at"),
            granted_scopes=tuple(payload.get("granted_scopes") or ()),
            open_id=payload.get("open_id"),
            union_id=payload.get("union_id"),
            account_identifier=payload.get("account_identifier"),
            provider=str(payload.get("provider") or "tiktok_login"),
        )

    def delete(self, reference: str) -> None:
        path = self._path(reference)
        if path.exists():
            path.unlink()


class EncryptedLocalTikTokCredentialStore:
    def __init__(self, root: Path, *, secret: str | None = None) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._secret = secret or os.environ.get("CIS_TIKTOK_CREDENTIAL_SECRET")
        if not self._secret:
            raise ValueError("Se requiere CIS_TIKTOK_CREDENTIAL_SECRET para el almacen cifrado de TikTok.")

    def _path(self, reference: str) -> Path:
        return self._root / f"{reference}.bin"

    def _encrypt(self, payload: dict[str, object], reference: str) -> bytes:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        salt = hashlib.sha256(reference.encode("utf-8")).digest()[:16]
        key = _derive_key(self._secret, salt)
        cipher = _xor_bytes(raw, key)
        return b".".join((base64.urlsafe_b64encode(salt), base64.urlsafe_b64encode(cipher)))

    def _decrypt(self, blob: bytes) -> dict[str, object]:
        salt_b64, cipher_b64 = blob.split(b".", 1)
        salt = base64.urlsafe_b64decode(salt_b64)
        cipher = base64.urlsafe_b64decode(cipher_b64)
        key = _derive_key(self._secret, salt)
        raw = _xor_bytes(cipher, key)
        return json.loads(raw.decode("utf-8"))

    def save(self, reference: str, bundle: TikTokCredentialBundle) -> None:
        self._path(reference).write_bytes(self._encrypt(bundle.to_dict(), reference))

    def load(self, reference: str) -> TikTokCredentialBundle | None:
        path = self._path(reference)
        if not path.exists():
            return None
        payload = self._decrypt(path.read_bytes())
        return TikTokCredentialBundle(
            client_id=payload.get("client_id"),
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type"),
            expires_at=payload.get("expires_at"),
            refresh_expires_at=payload.get("refresh_expires_at"),
            granted_scopes=tuple(payload.get("granted_scopes") or ()),
            open_id=payload.get("open_id"),
            union_id=payload.get("union_id"),
            account_identifier=payload.get("account_identifier"),
            provider=str(payload.get("provider") or "tiktok_login"),
        )

    def delete(self, reference: str) -> None:
        path = self._path(reference)
        if path.exists():
            path.unlink()
