"""Contratos de transaccion OAuth para el broker de Instagram."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .connection_types import InstagramAuthProvider
from .value_objects import InstagramOAuthTokenResult


class InstagramOAuthBrokerStatus(str, Enum):
    PENDING = "pending"
    CALLBACK_RECEIVED = "callback_received"
    COMPLETED = "completed"
    REDEEMED = "redeemed"
    FAILED = "failed"
    EXPIRED = "expired"


def generate_transaction_proof() -> str:
    return secrets.token_urlsafe(32)


def hash_transaction_proof(proof: str) -> str:
    return hashlib.sha256(proof.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class InstagramOAuthBrokerStartResult:
    transaction_id: str
    authorization_url: str
    expires_at: str
    state: str
    status: InstagramOAuthBrokerStatus = InstagramOAuthBrokerStatus.PENDING


@dataclass(frozen=True, slots=True)
class InstagramOAuthBrokerCallbackResult:
    transaction_id: str
    status: InstagramOAuthBrokerStatus
    browser_message: str
    expires_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class InstagramOAuthBrokerStatusResult:
    transaction_id: str
    status: InstagramOAuthBrokerStatus
    expires_at: str
    authorization_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class InstagramOAuthBrokerRedeemResult:
    transaction_id: str
    status: InstagramOAuthBrokerStatus
    token_result: InstagramOAuthTokenResult | None = None
    error_code: str | None = None
    error_message: str | None = None


class InstagramOAuthBrokerClient(Protocol):
    def start_transaction(
        self,
        *,
        creator_id: str,
        client_id: str,
        scopes: tuple[str, ...],
        transaction_proof: str,
        provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN,
    ) -> InstagramOAuthBrokerStartResult: ...

    def handle_callback(
        self,
        *,
        state: str,
        code: str | None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> InstagramOAuthBrokerCallbackResult: ...

    def poll_transaction(self, *, transaction_id: str, transaction_proof: str) -> InstagramOAuthBrokerStatusResult: ...
    def redeem_transaction(self, *, transaction_id: str, transaction_proof: str) -> InstagramOAuthBrokerRedeemResult: ...
