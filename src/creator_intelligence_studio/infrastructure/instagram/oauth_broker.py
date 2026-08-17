"""Broker OAuth minimal para Instagram."""

from __future__ import annotations

import logging
import secrets
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider
from creator_intelligence_studio.domain.instagram_integration.errors import InstagramAuthorizationError
from creator_intelligence_studio.domain.instagram_integration.oauth_broker import (
    InstagramOAuthBrokerCallbackResult,
    InstagramOAuthBrokerClient,
    InstagramOAuthBrokerRedeemResult,
    InstagramOAuthBrokerStartResult,
    InstagramOAuthBrokerStatus,
    InstagramOAuthBrokerStatusResult,
    generate_transaction_proof,
    hash_transaction_proof,
)
from creator_intelligence_studio.domain.instagram_integration.value_objects import (
    InstagramAuthProviderClient,
    InstagramOAuthTokenResult,
    READ_ONLY_SCOPES,
)
from creator_intelligence_studio.shared.dates import to_iso_z, utc_now


def _now() -> datetime:
    return utc_now()


def _sanitize_message(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class InstagramOAuthBrokerRecord:
    transaction_id: str
    creator_id: str
    client_id: str
    provider: str
    scopes_json: tuple[str, ...]
    state: str
    proof_hash: str
    authorization_url: str
    callback_url: str
    status: InstagramOAuthBrokerStatus
    created_at: datetime
    expires_at: datetime
    callback_received_at: datetime | None = None
    completed_at: datetime | None = None
    redeemed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    token_result: InstagramOAuthTokenResult | None = None


class InstagramOAuthBrokerStore(Protocol):
    def save(self, record: InstagramOAuthBrokerRecord) -> InstagramOAuthBrokerRecord: ...
    def get_by_transaction_id(self, transaction_id: str) -> InstagramOAuthBrokerRecord | None: ...
    def get_by_state(self, state: str) -> InstagramOAuthBrokerRecord | None: ...
    def delete(self, transaction_id: str) -> None: ...


class InMemoryInstagramOAuthBrokerStore:
    def __init__(self) -> None:
        self._records_by_transaction_id: dict[str, InstagramOAuthBrokerRecord] = {}
        self._record_ids_by_state: dict[str, str] = {}
        self._lock = threading.RLock()

    def save(self, record: InstagramOAuthBrokerRecord) -> InstagramOAuthBrokerRecord:
        with self._lock:
            self._records_by_transaction_id[record.transaction_id] = record
            self._record_ids_by_state[record.state] = record.transaction_id
            return record

    def get_by_transaction_id(self, transaction_id: str) -> InstagramOAuthBrokerRecord | None:
        with self._lock:
            return self._records_by_transaction_id.get(transaction_id)

    def get_by_state(self, state: str) -> InstagramOAuthBrokerRecord | None:
        with self._lock:
            transaction_id = self._record_ids_by_state.get(state)
            if transaction_id is None:
                return None
            return self._records_by_transaction_id.get(transaction_id)

    def delete(self, transaction_id: str) -> None:
        with self._lock:
            record = self._records_by_transaction_id.pop(transaction_id, None)
            if record is not None:
                self._record_ids_by_state.pop(record.state, None)


class InstagramOAuthBrokerService(InstagramOAuthBrokerClient):
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        callback_url: str,
        oauth_client: InstagramAuthProviderClient | None = None,
        store: InstagramOAuthBrokerStore | None = None,
        transaction_ttl_seconds: int = 600,
        logger: logging.Logger | None = None,
    ) -> None:
        if not client_id.strip():
            raise InstagramAuthorizationError("Se requiere client_id para el broker OAuth de Instagram.")
        if not client_secret.strip():
            raise InstagramAuthorizationError("Se requiere client_secret para el broker OAuth de Instagram.")
        if not callback_url.strip():
            raise InstagramAuthorizationError("Se requiere callback_url para el broker OAuth de Instagram.")
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.callback_url = callback_url.strip()
        self.oauth_client = oauth_client
        self.store = store or InMemoryInstagramOAuthBrokerStore()
        self.transaction_ttl_seconds = transaction_ttl_seconds
        self.logger = logger or logging.getLogger("creator_intelligence_studio.instagram.oauth_broker")

    def _validate_scopes(self, scopes: tuple[str, ...]) -> None:
        normalized = tuple(scope.strip() for scope in scopes if scope and scope.strip())
        if not normalized:
            raise InstagramAuthorizationError("Se requieren scopes para iniciar el broker OAuth.")
        if any(scope not in READ_ONLY_SCOPES for scope in normalized):
            raise InstagramAuthorizationError("Solo se permiten scopes aprobados de solo lectura.")

    def _now(self) -> datetime:
        return _now()

    def _expire_record(self, record: InstagramOAuthBrokerRecord) -> InstagramOAuthBrokerRecord:
        if record.status in {InstagramOAuthBrokerStatus.REDEEMED, InstagramOAuthBrokerStatus.FAILED, InstagramOAuthBrokerStatus.EXPIRED}:
            return record
        expired = replace(record, status=InstagramOAuthBrokerStatus.EXPIRED, error_code=record.error_code or "transaction_expired", error_message=record.error_message or "La transaccion expiro.")
        return self.store.save(expired)

    def _get_active_record(self, transaction_id: str) -> InstagramOAuthBrokerRecord:
        record = self.store.get_by_transaction_id(transaction_id)
        if record is None:
            raise InstagramAuthorizationError("La transaccion OAuth de Instagram no existe.")
        if self._now() > record.expires_at:
            record = self._expire_record(record)
            raise InstagramAuthorizationError("La transaccion OAuth de Instagram expiro.")
        return record

    def _proof_matches(self, record: InstagramOAuthBrokerRecord, transaction_proof: str) -> bool:
        return record.proof_hash == hash_transaction_proof(transaction_proof)

    def start_transaction(
        self,
        *,
        creator_id: str,
        client_id: str,
        scopes: tuple[str, ...],
        transaction_proof: str | None = None,
        provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN,
    ) -> InstagramOAuthBrokerStartResult:
        if provider != InstagramAuthProvider.INSTAGRAM_LOGIN:
            raise InstagramAuthorizationError("Solo Instagram Login esta habilitado para el broker v35-C1.")
        self._validate_scopes(scopes)
        if client_id.strip() != self.client_id:
            raise InstagramAuthorizationError("El client_id no coincide con la configuracion del broker OAuth de Instagram.")
        proof = transaction_proof or generate_transaction_proof()
        state = secrets.token_urlsafe(24)
        transaction_id = uuid4().hex
        oauth_client = self.oauth_client
        if oauth_client is None:
            raise InstagramAuthorizationError("El broker OAuth de Instagram no tiene cliente de proveedor configurado.")
        authorization = oauth_client.begin_authorization(
            client_id=self.client_id,
            scopes=scopes,
            redirect_uri=self.callback_url,
            state=state,
        )
        now = self._now()
        record = InstagramOAuthBrokerRecord(
            transaction_id=transaction_id,
            creator_id=creator_id,
            client_id=self.client_id,
            provider=provider.value,
            scopes_json=tuple(scopes),
            state=state,
            proof_hash=hash_transaction_proof(proof),
            authorization_url=authorization.authorization_url,
            callback_url=self.callback_url,
            status=InstagramOAuthBrokerStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(seconds=self.transaction_ttl_seconds),
        )
        self.store.save(record)
        return InstagramOAuthBrokerStartResult(
            transaction_id=record.transaction_id,
            authorization_url=record.authorization_url,
            expires_at=to_iso_z(record.expires_at),
            state=record.state,
            status=record.status,
        )

    def handle_callback(
        self,
        *,
        state: str,
        code: str | None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> InstagramOAuthBrokerCallbackResult:
        record = self.store.get_by_state(state)
        if record is None:
            raise InstagramAuthorizationError("El estado OAuth de Instagram no coincide.")
        if self._now() > record.expires_at:
            expired = self._expire_record(record)
            return InstagramOAuthBrokerCallbackResult(
                transaction_id=expired.transaction_id,
                status=expired.status,
                browser_message="La transaccion expiro. Vuelve a intentar la conexion.",
                expires_at=to_iso_z(expired.expires_at),
                error_code=expired.error_code,
                error_message=expired.error_message,
            )
        if record.status in {InstagramOAuthBrokerStatus.COMPLETED, InstagramOAuthBrokerStatus.REDEEMED}:
            return InstagramOAuthBrokerCallbackResult(
                transaction_id=record.transaction_id,
                status=record.status,
                browser_message="La transaccion ya fue procesada.",
                expires_at=to_iso_z(record.expires_at),
                error_code="replay",
                error_message="La transaccion OAuth ya fue procesada.",
            )
        if error is not None:
            failed = replace(
                record,
                status=InstagramOAuthBrokerStatus.FAILED,
                error_code=_sanitize_message(error) or "provider_authorization_denied",
                error_message=_sanitize_message(error_description) or "La autorizacion fue rechazada por el proveedor.",
            )
            self.store.save(failed)
            return InstagramOAuthBrokerCallbackResult(
                transaction_id=failed.transaction_id,
                status=failed.status,
                browser_message="Instagram no autorizo la conexion. Puedes cerrar esta ventana.",
                expires_at=to_iso_z(failed.expires_at),
                error_code=failed.error_code,
                error_message=failed.error_message,
            )
        if not code:
            failed = replace(
                record,
                status=InstagramOAuthBrokerStatus.FAILED,
                error_code="missing_code",
                error_message="No se recibio el codigo de autorizacion.",
            )
            self.store.save(failed)
            return InstagramOAuthBrokerCallbackResult(
                transaction_id=failed.transaction_id,
                status=failed.status,
                browser_message="No se recibio el codigo de autorizacion.",
                expires_at=to_iso_z(failed.expires_at),
                error_code=failed.error_code,
                error_message=failed.error_message,
            )
        if self.oauth_client is None:
            failed = replace(
                record,
                status=InstagramOAuthBrokerStatus.FAILED,
                error_code="broker_unavailable",
                error_message="El broker OAuth de Instagram no esta disponible.",
            )
            self.store.save(failed)
            return InstagramOAuthBrokerCallbackResult(
                transaction_id=failed.transaction_id,
                status=failed.status,
                browser_message="El broker de Instagram no esta disponible.",
                expires_at=to_iso_z(failed.expires_at),
                error_code=failed.error_code,
                error_message=failed.error_message,
            )
        try:
            token_result = self.oauth_client.exchange_code(
                client_id=record.client_id,
                client_secret=self.client_secret,
                code=code,
                redirect_uri=self.callback_url,
            )
        except Exception as exc:
            failed = replace(
                record,
                status=InstagramOAuthBrokerStatus.FAILED,
                error_code="token_exchange_failed",
                error_message=_sanitize_message(exc) or "La conversion del codigo de autorizacion fallo.",
            )
            self.store.save(failed)
            return InstagramOAuthBrokerCallbackResult(
                transaction_id=failed.transaction_id,
                status=failed.status,
                browser_message="No se pudo completar el intercambio de token.",
                expires_at=to_iso_z(failed.expires_at),
                error_code=failed.error_code,
                error_message=failed.error_message,
            )
        completed = replace(
            record,
            status=InstagramOAuthBrokerStatus.COMPLETED,
            callback_received_at=self._now(),
            completed_at=self._now(),
            error_code=None,
            error_message=None,
            token_result=token_result,
        )
        self.store.save(completed)
        self.logger.info("instagram_oauth_broker.callback_completed status=%s", completed.status.value)
        return InstagramOAuthBrokerCallbackResult(
            transaction_id=completed.transaction_id,
            status=completed.status,
            browser_message="Instagram connected. You can return to Creator Intelligence Studio.",
            expires_at=to_iso_z(completed.expires_at),
        )

    def poll_transaction(self, *, transaction_id: str, transaction_proof: str) -> InstagramOAuthBrokerStatusResult:
        record = self._get_active_record(transaction_id)
        if not self._proof_matches(record, transaction_proof):
            raise InstagramAuthorizationError("La prueba de transaccion no coincide.")
        return InstagramOAuthBrokerStatusResult(
            transaction_id=record.transaction_id,
            status=record.status,
            expires_at=to_iso_z(record.expires_at),
            authorization_url=None if record.status != InstagramOAuthBrokerStatus.PENDING else record.authorization_url,
            error_code=record.error_code,
            error_message=record.error_message,
        )

    def redeem_transaction(self, *, transaction_id: str, transaction_proof: str) -> InstagramOAuthBrokerRedeemResult:
        record = self._get_active_record(transaction_id)
        if not self._proof_matches(record, transaction_proof):
            raise InstagramAuthorizationError("La prueba de transaccion no coincide.")
        if record.status == InstagramOAuthBrokerStatus.REDEEMED:
            raise InstagramAuthorizationError("La transaccion OAuth ya fue redimida.")
        if record.status == InstagramOAuthBrokerStatus.FAILED:
            raise InstagramAuthorizationError(record.error_message or "La transaccion OAuth fallo.")
        if record.status != InstagramOAuthBrokerStatus.COMPLETED or record.token_result is None:
            raise InstagramAuthorizationError("La transaccion OAuth aun no esta lista para redencion.")
        token_result = record.token_result
        redeemed = replace(
            record,
            status=InstagramOAuthBrokerStatus.REDEEMED,
            redeemed_at=self._now(),
            token_result=None,
        )
        self.store.save(redeemed)
        return InstagramOAuthBrokerRedeemResult(
            transaction_id=redeemed.transaction_id,
            status=redeemed.status,
            token_result=token_result,
        )
