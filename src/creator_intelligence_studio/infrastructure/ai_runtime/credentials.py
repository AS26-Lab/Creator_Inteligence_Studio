"""Credential storage for AI providers."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class CredentialBackendError(RuntimeError):
    """Raised when a backend cannot store or load secrets."""


class CredentialNotAvailableError(CredentialBackendError):
    """Raised when a backend is unavailable on this platform."""


class CredentialBackend(Protocol):
    def save(self, reference: str, secret: str) -> None: ...

    def load(self, reference: str) -> str | None: ...

    def delete(self, reference: str) -> None: ...

    def is_available(self) -> bool: ...


class InMemoryCredentialBackend:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def save(self, reference: str, secret: str) -> None:
        self._values[reference] = secret

    def load(self, reference: str) -> str | None:
        return self._values.get(reference)

    def delete(self, reference: str) -> None:
        self._values.pop(reference, None)

    def is_available(self) -> bool:
        return True


class DevelopmentEnvironmentCredentialBackend:
    """Explicit dev fallback that keeps values in process environment only."""

    def __init__(self, prefix: str = "CIS_") -> None:
        self.prefix = prefix

    def _env_key(self, reference: str) -> str:
        return f"{self.prefix}{reference}".upper().replace(".", "_").replace("-", "_")

    def save(self, reference: str, secret: str) -> None:
        os.environ[self._env_key(reference)] = secret

    def load(self, reference: str) -> str | None:
        return os.environ.get(self._env_key(reference))

    def delete(self, reference: str) -> None:
        os.environ.pop(self._env_key(reference), None)

    def is_available(self) -> bool:
        return True


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
    _fields_ = [
        ("Keyword", wintypes.LPWSTR),
        ("Flags", wintypes.DWORD),
        ("ValueSize", wintypes.DWORD),
        ("Value", ctypes.POINTER(ctypes.c_byte)),
    ]


class WindowsCredentialManagerBackend:
    """Windows Credential Manager backend using CredWrite/CredRead."""

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTEW)),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    def __init__(self, target_prefix: str = "CreatorIntelligenceStudio") -> None:
        self.target_prefix = target_prefix
        self._cred_write = None
        self._cred_read = None
        self._cred_delete = None
        self._cred_free = None
        self._available = os.name == "nt"
        if self._available:
            try:
                self._cred_write = ctypes.windll.advapi32.CredWriteW
                self._cred_read = ctypes.windll.advapi32.CredReadW
                self._cred_delete = ctypes.windll.advapi32.CredDeleteW
                self._cred_free = ctypes.windll.advapi32.CredFree
            except AttributeError:
                self._available = False

    def _target(self, reference: str) -> str:
        return f"{self.target_prefix}:{reference}"

    def save(self, reference: str, secret: str) -> None:
        if not self.is_available():
            raise CredentialNotAvailableError("Windows Credential Manager is not available.")
        blob = secret.encode("utf-8")
        buffer = (ctypes.c_byte * len(blob))(*blob)
        credential = self.CREDENTIALW()
        credential.Flags = 0
        credential.Type = self.CRED_TYPE_GENERIC
        credential.TargetName = self._target(reference)
        credential.Comment = None
        credential.LastWritten = FILETIME(0, 0)
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
        credential.Persist = self.CRED_PERSIST_LOCAL_MACHINE
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.TargetAlias = None
        credential.UserName = None
        if not self._cred_write(ctypes.byref(credential), 0):
            raise CredentialBackendError(f"Unable to save credential '{reference}'.")

    def load(self, reference: str) -> str | None:
        if not self.is_available():
            raise CredentialNotAvailableError("Windows Credential Manager is not available.")
        cred_ptr = ctypes.POINTER(self.CREDENTIALW)()
        if not self._cred_read(self._target(reference), self.CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr)):
            return None
        try:
            credential = cred_ptr.contents
            if credential.CredentialBlobSize == 0 or not credential.CredentialBlob:
                return ""
            blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return blob.decode("utf-8")
        finally:
            self._cred_free(cred_ptr)

    def delete(self, reference: str) -> None:
        if not self.is_available():
            raise CredentialNotAvailableError("Windows Credential Manager is not available.")
        if not self._cred_delete(self._target(reference), self.CRED_TYPE_GENERIC, 0):
            return

    def is_available(self) -> bool:
        return bool(self._available)


@dataclass(frozen=True, slots=True)
class CredentialStore:
    """Typed wrapper around a backend."""

    backend: CredentialBackend

    def is_available(self) -> bool:
        return self.backend.is_available()

    def mask(self, secret: str | None) -> str:
        if not secret:
            return "no configurado"
        tail = secret[-4:] if len(secret) >= 4 else secret
        return f"{'•' * 8}{tail}"

    def save(self, reference: str, secret: str) -> None:
        self.backend.save(reference, secret)

    def load(self, reference: str) -> str | None:
        return self.backend.load(reference)

    def delete(self, reference: str) -> None:
        self.backend.delete(reference)

    @classmethod
    def build_default(cls) -> "CredentialStore":
        if os.environ.get("CIS_ENABLE_ENV_CREDENTIALS") == "1":
            return cls(DevelopmentEnvironmentCredentialBackend())
        backend = WindowsCredentialManagerBackend()
        if backend.is_available():
            return cls(backend)
        return cls(DevelopmentEnvironmentCredentialBackend())

    @classmethod
    def build_memory(cls) -> "CredentialStore":
        return cls(InMemoryCredentialBackend())

    @staticmethod
    def reference_for_provider(provider: str) -> str:
        return f"ai.{provider}.api_key"
