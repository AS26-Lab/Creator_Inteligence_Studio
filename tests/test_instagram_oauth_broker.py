from __future__ import annotations

import io
import logging
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from creator_intelligence_studio.application.services.instagram_integration_service import build_instagram_integration_service
from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider, InstagramConnectionStatus
from creator_intelligence_studio.domain.instagram_integration.errors import InstagramAuthorizationError
from creator_intelligence_studio.domain.instagram_integration.oauth_broker import (
    InstagramOAuthBrokerStatus,
    generate_transaction_proof,
)
from creator_intelligence_studio.domain.creators.entities import Creator, CreatorStatus
from creator_intelligence_studio.domain.instagram_integration.value_objects import (
    READ_ONLY_SCOPES,
    InstagramOAuthAuthorizationResult,
    InstagramOAuthTokenResult,
    build_instagram_credential_reference,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.instagram.oauth_broker import (
    InMemoryInstagramOAuthBrokerStore,
    InstagramOAuthBrokerService,
)
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_repository import SQLiteCreatorRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_instagram_repository import SQLiteInstagramRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


def make_settings(root: Path) -> AppSettings:
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
        log_level="INFO",
        data_directory=str(root / "data"),
        logs_directory=str(root / "logs"),
        models_directory=str(root / "models"),
        artifacts_directory=str(root / "artifacts"),
        preferred_compute_backend="cuda",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
    )


def make_paths(root: Path, settings: AppSettings) -> ProjectPaths:
    return ProjectPaths.from_settings(root, settings)


class MemoryInstagramCredentialStore:
    def __init__(self) -> None:
        self.saved: dict[str, object] = {}

    def save(self, reference: str, bundle) -> None:
        self.saved[reference] = bundle

    def load(self, reference: str):
        return self.saved.get(reference)

    def delete(self, reference: str) -> None:
        self.saved.pop(reference, None)


class FakeInstagramOAuthClient:
    def __init__(self) -> None:
        self.begin_calls: list[tuple[str, tuple[str, ...], str | None, str | None]] = []
        self.exchange_calls: list[tuple[str, str | None, str, str]] = []
        self._token_user_ids = {
            "code-a": "ig-a",
            "code-b": "ig-a",
            "code-personal": "ig-personal",
        }

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> InstagramOAuthAuthorizationResult:
        self.begin_calls.append((client_id, scopes, redirect_uri, state))
        redirect = redirect_uri or "https://broker.example.test/oauth/instagram/callback"
        state = state or "state"
        scope_text = ",".join(scopes)
        return InstagramOAuthAuthorizationResult(
            authorization_url=f"https://www.instagram.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect}&scope={scope_text}&state={state}",
            state=state,
            redirect_uri=redirect,
            provider=InstagramAuthProvider.INSTAGRAM_LOGIN,
            code_challenge="challenge",
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> InstagramOAuthTokenResult:
        self.exchange_calls.append((client_id, client_secret, code, redirect_uri))
        user_id = self._token_user_ids.get(code, "ig-a")
        return InstagramOAuthTokenResult(
            access_token=f"access-{code}",
            refresh_token=f"refresh-{code}",
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            instagram_user_id=user_id,
            expires_at="2026-08-01T00:00:00Z",
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> InstagramOAuthTokenResult:
        raise NotImplementedError

    def revoke(self, token: str) -> bool:
        return True

    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]:
        return {"instagram_user_id": "ig-a", "granted_scopes": scopes, "missing_scopes": ()}


class InstagramOAuthBrokerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tempdir = tempfile.TemporaryDirectory()
        root = Path(cls._tempdir.name)
        cls._settings = make_settings(root)
        cls._paths = make_paths(root, cls._settings)
        cls._paths.ensure_runtime_directories()
        cls._database = build_database(cls._settings, cls._paths)
        with cls._database.connect() as connection:
            run_migrations(connection)
        cls._creator_repository = SQLiteCreatorRepository(cls._database)
        cls._repository = SQLiteInstagramRepository(cls._database)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tempdir.cleanup()

    def _creator_id(self) -> str:
        return f"creator-{self._testMethodName}"

    def _make_bundle(self):
        credential_store = MemoryInstagramCredentialStore()
        oauth_client = FakeInstagramOAuthClient()
        broker = InstagramOAuthBrokerService(
            client_id="client-id",
            client_secret="client-secret",
            callback_url="https://broker.example.test/oauth/instagram/callback",
            oauth_client=oauth_client,
            store=InMemoryInstagramOAuthBrokerStore(),
            transaction_ttl_seconds=60,
        )
        creator_id = self._creator_id()
        if self._creator_repository.get_by_id(creator_id) is None:
            self._creator_repository.create(
                Creator(
                    id=creator_id,
                    display_name=f"Creator {creator_id}",
                    slug=creator_id,
                    description=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    status=CreatorStatus.ACTIVE,
                )
            )
        service = build_instagram_integration_service(
            settings=self._settings,
            paths=self._paths,
            repository=self._repository,
            database=self._database,
            oauth_client=oauth_client,
            oauth_broker=broker,
            credential_store=credential_store,
        )
        return {
            "root": Path(self._tempdir.name),
            "settings": self._settings,
            "paths": self._paths,
            "database": self._database,
            "repository": self._repository,
            "credential_store": credential_store,
            "oauth_client": oauth_client,
            "broker": broker,
            "service": service,
        }

    def test_start_transaction_generates_unique_transaction_and_redacts_proof(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        creator_id = self._creator_id()
        proof_a = generate_transaction_proof()
        proof_b = generate_transaction_proof()
        start_a = broker.start_transaction(
            creator_id=creator_id,
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof_a,
        )
        start_b = broker.start_transaction(
            creator_id=creator_id,
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof_b,
        )
        self.assertNotEqual(start_a.transaction_id, start_b.transaction_id)
        self.assertNotEqual(start_a.state, start_b.state)
        self.assertNotIn(proof_a, start_a.authorization_url)
        self.assertNotIn(proof_b, start_b.authorization_url)
        self.assertIn("https://broker.example.test/oauth/instagram/callback", start_a.authorization_url)

    def test_callback_success_and_single_use_redeem(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        creator_id = self._creator_id()
        proof = generate_transaction_proof()
        start = broker.start_transaction(
            creator_id=creator_id,
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof,
        )
        callback = broker.handle_callback(state=start.state, code="code-a")
        self.assertEqual(callback.status, InstagramOAuthBrokerStatus.COMPLETED)
        self.assertNotIn("access-", callback.browser_message)
        status = broker.poll_transaction(transaction_id=start.transaction_id, transaction_proof=proof)
        self.assertEqual(status.status, InstagramOAuthBrokerStatus.COMPLETED)
        redeem = broker.redeem_transaction(transaction_id=start.transaction_id, transaction_proof=proof)
        self.assertIsNotNone(redeem.token_result)
        self.assertEqual(redeem.token_result.access_token, "access-code-a")
        with self.assertRaises(InstagramAuthorizationError):
            broker.redeem_transaction(transaction_id=start.transaction_id, transaction_proof=proof)

    def test_expired_transaction_rejected(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        creator_id = self._creator_id()
        proof = generate_transaction_proof()
        start = broker.start_transaction(
            creator_id=creator_id,
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof,
        )
        record = broker.store.get_by_transaction_id(start.transaction_id)
        assert record is not None
        broker.store.save(replace(record, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        with self.assertRaises(InstagramAuthorizationError):
            broker.poll_transaction(transaction_id=start.transaction_id, transaction_proof=proof)
        with self.assertRaises(InstagramAuthorizationError):
            broker.redeem_transaction(transaction_id=start.transaction_id, transaction_proof=proof)

    def test_incorrect_proof_rejected(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        creator_id = self._creator_id()
        proof = generate_transaction_proof()
        start = broker.start_transaction(
            creator_id=creator_id,
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof,
        )
        with self.assertRaises(InstagramAuthorizationError):
            broker.poll_transaction(transaction_id=start.transaction_id, transaction_proof=generate_transaction_proof())
        with self.assertRaises(InstagramAuthorizationError):
            broker.redeem_transaction(transaction_id=start.transaction_id, transaction_proof=generate_transaction_proof())

    def test_state_mismatch_rejected(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        _ = self._creator_id()
        with self.assertRaises(InstagramAuthorizationError):
            broker.handle_callback(state="wrong-state", code="code-a")

    def test_callback_denial_is_sanitized(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        creator_id = self._creator_id()
        proof = generate_transaction_proof()
        start = broker.start_transaction(
            creator_id=creator_id,
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof,
        )
        callback = broker.handle_callback(state=start.state, code=None, error="access_denied", error_description="user cancelled")
        self.assertEqual(callback.status, InstagramOAuthBrokerStatus.FAILED)
        self.assertEqual(callback.error_code, "access_denied")
        self.assertEqual(callback.error_message, "user cancelled")
        with self.assertRaises(InstagramAuthorizationError):
            broker.redeem_transaction(transaction_id=start.transaction_id, transaction_proof=proof)

    def test_service_complete_transaction_persists_canonical_connection_and_credential(self) -> None:
        bundle = self._make_bundle()
        service = bundle["service"]
        broker = bundle["broker"]
        credential_store = bundle["credential_store"]
        creator_id = self._creator_id()
        proof = generate_transaction_proof()
        start = service.start_oauth_transaction(creator_id=creator_id, client_id="client-id", transaction_proof=proof)
        broker.handle_callback(state=start.state, code="code-a")
        result = service.complete_oauth_transaction(creator_id=creator_id, transaction_id=start.transaction_id, transaction_proof=proof)
        self.assertEqual(result.connection.status, InstagramConnectionStatus.PENDING)
        self.assertEqual(result.warnings, ("authorized_pending_profile",))
        expected_reference = build_instagram_credential_reference(creator_id=creator_id, instagram_user_id="ig-a")
        self.assertEqual(result.connection.credential_reference, expected_reference)
        self.assertIsNotNone(credential_store.load(expected_reference))
        self.assertEqual(len(service.list_connections(creator_id)), 1)
        self.assertEqual(service.list_connections(creator_id)[0].credential_reference, expected_reference)

    def test_repeated_reconnect_reuses_canonical_connection(self) -> None:
        bundle = self._make_bundle()
        service = bundle["service"]
        broker = bundle["broker"]
        creator_id = self._creator_id()
        proof_a = generate_transaction_proof()
        start_a = service.start_oauth_transaction(creator_id=creator_id, client_id="client-id", transaction_proof=proof_a)
        broker.handle_callback(state=start_a.state, code="code-a")
        result_a = service.complete_oauth_transaction(creator_id=creator_id, transaction_id=start_a.transaction_id, transaction_proof=proof_a)
        proof_b = generate_transaction_proof()
        start_b = service.start_oauth_transaction(creator_id=creator_id, client_id="client-id", transaction_proof=proof_b)
        broker.handle_callback(state=start_b.state, code="code-b")
        result_b = service.complete_oauth_transaction(creator_id=creator_id, transaction_id=start_b.transaction_id, transaction_proof=proof_b)
        self.assertEqual(result_a.connection.credential_reference, result_b.connection.credential_reference)
        self.assertEqual(len(service.list_connections(creator_id)), 1)

    def test_token_never_appears_in_logs(self) -> None:
        bundle = self._make_bundle()
        broker = bundle["broker"]
        _ = self._creator_id()
        proof = generate_transaction_proof()
        logger = logging.getLogger("creator_intelligence_studio.instagram.oauth_broker")
        logger.setLevel(logging.INFO)
        buffer = io.StringIO()
        handler = logging.StreamHandler(buffer)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        start = broker.start_transaction(
            creator_id="creator-a",
            client_id="client-id",
            scopes=READ_ONLY_SCOPES,
            transaction_proof=proof,
        )
        broker.handle_callback(state=start.state, code="code-a")
        broker.redeem_transaction(transaction_id=start.transaction_id, transaction_proof=proof)
        logs = buffer.getvalue()
        self.assertNotIn("access-code-a", logs)
        self.assertNotIn(proof, logs)
        self.assertNotIn("client-secret", logs)

    def test_sqlite_schema_does_not_store_instagram_tokens(self) -> None:
        bundle = self._make_bundle()
        database = bundle["database"]
        with database.connect() as connection:
            columns = [row["name"] for row in connection.execute("PRAGMA table_info(instagram_connections)")]
        self.assertNotIn("access_token", columns)
        self.assertNotIn("refresh_token", columns)
        self.assertNotIn("authorization_code", columns)
        self.assertNotIn("pkce_verifier", columns)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
