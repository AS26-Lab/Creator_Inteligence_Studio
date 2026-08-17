"""Almacenamiento local de credenciales para YouTube."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from creator_intelligence_studio.infrastructure.ai_runtime.credentials import (
    CredentialStore as _SecretCredentialStore,
    WindowsCredentialManagerBackend,
)


@dataclass(frozen=True, slots=True)
class CredentialBundle:
    access_token: str | None
    refresh_token: str | None
    token_type: str | None
    expires_at: str | None
    granted_scopes: tuple[str, ...]
    google_account_identifier: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "granted_scopes": list(self.granted_scopes),
            "google_account_identifier": self.google_account_identifier,
        }


class CredentialStore(Protocol):
    def save(self, reference: str, bundle: CredentialBundle) -> None: ...
    def load(self, reference: str) -> CredentialBundle | None: ...
    def delete(self, reference: str) -> None: ...


def _derive_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 120_000, dklen=32)


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


class DevelopmentCredentialStore:
    """Fallback explicito para desarrollo. No guardar en produccion."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, reference: str) -> Path:
        return self._root / f"{reference}.json"

    def save(self, reference: str, bundle: CredentialBundle) -> None:
        self._path(reference).write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, reference: str) -> CredentialBundle | None:
        path = self._path(reference)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CredentialBundle(
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type"),
            expires_at=payload.get("expires_at"),
            granted_scopes=tuple(payload.get("granted_scopes") or ()),
            google_account_identifier=payload.get("google_account_identifier"),
        )

    def delete(self, reference: str) -> None:
        path = self._path(reference)
        if path.exists():
            path.unlink()


class EncryptedLocalCredentialStore:
    """Cifrado local simple con clave administrada fuera de SQLite."""

    def __init__(self, root: Path, *, secret: str | None = None) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._secret = secret or os.environ.get("CIS_YOUTUBE_CREDENTIAL_SECRET")
        if not self._secret:
            raise ValueError("Se requiere CIS_YOUTUBE_CREDENTIAL_SECRET para el almacén cifrado.")

    def _path(self, reference: str) -> Path:
        return self._root / f"{reference}.bin"

    def _encrypt(self, payload: dict[str, object], reference: str) -> bytes:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        salt = hashlib.sha256(reference.encode("utf-8")).digest()[:16]
        key = _derive_key(self._secret, salt)
        cipher = _xor_bytes(raw, key)
        return b"".join((base64.urlsafe_b64encode(salt), b".", base64.urlsafe_b64encode(cipher)))

    def _decrypt(self, blob: bytes) -> dict[str, object]:
        salt_b64, cipher_b64 = blob.split(b".", 1)
        salt = base64.urlsafe_b64decode(salt_b64)
        cipher = base64.urlsafe_b64decode(cipher_b64)
        key = _derive_key(self._secret, salt)
        raw = _xor_bytes(cipher, key)
        return json.loads(raw.decode("utf-8"))

    def save(self, reference: str, bundle: CredentialBundle) -> None:
        self._path(reference).write_bytes(self._encrypt(bundle.to_dict(), reference))

    def load(self, reference: str) -> CredentialBundle | None:
        path = self._path(reference)
        if not path.exists():
            return None
        payload = self._decrypt(path.read_bytes())
        return CredentialBundle(
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type"),
            expires_at=payload.get("expires_at"),
            granted_scopes=tuple(payload.get("granted_scopes") or ()),
            google_account_identifier=payload.get("google_account_identifier"),
        )

    def delete(self, reference: str) -> None:
        path = self._path(reference)
        if path.exists():
            path.unlink()


class WindowsSecureCredentialStore:
    """Wrapper de Windows Credential Manager para credenciales de YouTube."""

    def __init__(self, *, target_prefix: str = "CreatorIntelligenceStudio.YouTube") -> None:
        self._backend = WindowsCredentialManagerBackend(target_prefix=target_prefix)
        self._store = _SecretCredentialStore(self._backend)

    def is_available(self) -> bool:
        return self._backend.is_available()

    def save(self, reference: str, bundle: CredentialBundle) -> None:
        self._store.save(reference, json.dumps(bundle.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True))

    def load(self, reference: str) -> CredentialBundle | None:
        payload = self._store.load(reference)
        if payload is None:
            return None
        try:
            data = json.loads(payload)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return CredentialBundle(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type"),
            expires_at=data.get("expires_at"),
            granted_scopes=tuple(data.get("granted_scopes") or ()),
            google_account_identifier=data.get("google_account_identifier"),
        )

    def delete(self, reference: str) -> None:
        self._store.delete(reference)


def build_default_youtube_credential_store(root: Path, *, environment: str | None = None) -> CredentialStore:
    windows_store = WindowsSecureCredentialStore()
    if windows_store.is_available():
        return windows_store
    secret = os.environ.get("CIS_YOUTUBE_CREDENTIAL_SECRET")
    if secret:
        return EncryptedLocalCredentialStore(root, secret=secret)
    if environment in {"development", "test"}:
        return DevelopmentCredentialStore(root / "development")
    raise ValueError("No secure credential store is available for YouTube.")
