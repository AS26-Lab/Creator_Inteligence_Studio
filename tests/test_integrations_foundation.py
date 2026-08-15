from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.application.services.integration_service import IntegrationService
from creator_intelligence_studio.domain.integrations import (
    IntegrationAccountLinkRequest,
    IntegrationAccountStatus,
    IntegrationAuthType,
    IntegrationCapability,
    IntegrationErrorCategory,
    IntegrationHealthStatus,
    IntegrationRateLimitState,
    IntegrationReadRequest,
    IntegrationWriteRequest,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic import collect_environment_diagnostic
from creator_intelligence_studio.infrastructure.integrations import (
    FakeIntegrationConnector,
    IntegrationRegistry,
    LocalNoAuthIntegrationConnector,
    build_default_integration_registry,
)
from creator_intelligence_studio.presentation.cli.integrations_cli import build_integrations_parser, handle_integrations_command
from creator_intelligence_studio.shared.paths import ProjectPaths


def _service() -> IntegrationService:
    return IntegrationService(registry=build_default_integration_registry())


def _fake_service() -> IntegrationService:
    return IntegrationService(registry=IntegrationRegistry((FakeIntegrationConnector(),)))


def _linked_account(service: IntegrationService, *, creator_id: str = "creator-a", external_account_id: str = "acct-a"):
    return service.link_account(
        IntegrationAccountLinkRequest(
            creator_id=creator_id,
            connector_id="fake.connector",
            external_account_id=external_account_id,
            display_name=f"{creator_id} account",
            auth_type=IntegrationAuthType.LOCAL_NO_AUTH,
        )
    )


class IntegrationFoundationTests(unittest.TestCase):
    def test_registry_summary_and_contract(self) -> None:
        service = _service()

        summary = service.summary()

        self.assertEqual(summary.integration_contract_version, "integration-contract-v1")
        self.assertEqual(summary.registered_connector_count, 3)
        self.assertEqual(summary.registered_connector_ids, ("fake.connector", "local.connector", "youtube.connector"))
        self.assertEqual([item.connector_id for item in service.list_connectors()], ["fake.connector", "local.connector", "youtube.connector"])

    def test_duplicate_connector_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            IntegrationRegistry((FakeIntegrationConnector(), FakeIntegrationConnector()))

    def test_creator_ownership_and_multiple_accounts(self) -> None:
        service = _fake_service()
        account_a = _linked_account(service, creator_id="creator-a", external_account_id="acct-a")
        account_b = _linked_account(service, creator_id="creator-b", external_account_id="acct-b")

        self.assertEqual(service.list_accounts("creator-a"), (account_a,))
        self.assertEqual(service.list_accounts("creator-b"), (account_b,))
        self.assertIsNone(service.get_account(creator_id="creator-a", account_id=account_b.id))
        self.assertFalse(service.unlink_account(creator_id="creator-a", account_id=account_b.id))

    def test_read_dispatch_and_normalized_results(self) -> None:
        service = _fake_service()
        account = _linked_account(service)

        content_result = service.read(
            IntegrationReadRequest(
                request_id="read-1",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.CONTENT_LIST_READ,
            )
        )
        analytics_result = service.read(
            IntegrationReadRequest(
                request_id="read-2",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.ANALYTICS_READ,
            )
        )

        self.assertTrue(content_result.success)
        self.assertEqual(len(content_result.resources), 2)
        self.assertEqual(content_result.next_page_token, "page-2")
        self.assertTrue(analytics_result.success)
        self.assertEqual(len(analytics_result.analytics), 3)
        self.assertTrue(any(metric.value is None and metric.availability == "missing" for metric in analytics_result.analytics))

    def test_error_taxonomy_and_rate_limits(self) -> None:
        service = _fake_service()
        account = _linked_account(service)
        connector = service.registry.get(account.connector_id)
        assert connector is not None

        scenarios = [
            ("expired", IntegrationAccountStatus.EXPIRED, None, IntegrationErrorCategory.AUTHENTICATION_EXPIRED, False),
            ("permission_missing", IntegrationAccountStatus.PERMISSION_MISSING, None, IntegrationErrorCategory.PERMISSION_DENIED, False),
            ("provider_unavailable", IntegrationAccountStatus.CONNECTED, False, IntegrationErrorCategory.PROVIDER_UNAVAILABLE, True),
        ]

        for _, status, available, expected_category, expected_retryable in scenarios:
            with self.subTest(status=status.value):
                connector.set_account_status(account.id, status)
                if available is not None:
                    connector.set_available(available)
                result = service.read(
                    IntegrationReadRequest(
                        request_id=f"read-{status.value}",
                        creator_id=account.creator_id,
                        connector_id=account.connector_id,
                        account_id=account.id,
                        capability=IntegrationCapability.CONTENT_LIST_READ,
                    )
                )
                self.assertFalse(result.success)
                self.assertEqual(result.error.category, expected_category)
                self.assertEqual(result.error.retryable, expected_retryable)
                connector.set_available(True)
                connector.set_account_status(account.id, IntegrationAccountStatus.CONNECTED)

        connector.set_rate_limit(account.id, IntegrationRateLimitState(limited=True, remaining=0, retry_after_seconds=15.0))
        rate_limited = service.read(
            IntegrationReadRequest(
                request_id="read-rate-limit",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.CONTENT_LIST_READ,
            )
        )
        self.assertFalse(rate_limited.success)
        self.assertEqual(rate_limited.error.category, IntegrationErrorCategory.RATE_LIMITED)
        self.assertTrue(rate_limited.error.retryable)
        self.assertTrue(rate_limited.rate_limit_state.limited)

    def test_write_approval_and_idempotency(self) -> None:
        service = _fake_service()
        account = _linked_account(service)

        approval_required = service.write(
            IntegrationWriteRequest(
                request_id="write-1",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.CONTENT_PUBLISH,
                payload={"title": "Draft"},
                approved_by_user=False,
                idempotency_key="idem-1",
            )
        )
        invalid_request = service.write(
            IntegrationWriteRequest(
                request_id="write-2",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.CONTENT_PUBLISH,
                payload={"title": "Draft"},
                approved_by_user=True,
            )
        )
        write_one = service.write(
            IntegrationWriteRequest(
                request_id="write-3",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.CONTENT_PUBLISH,
                payload={"title": "Draft"},
                approved_by_user=True,
                approval_reference="approval-1",
                idempotency_key="idem-2",
            )
        )
        write_two = service.write(
            IntegrationWriteRequest(
                request_id="write-4",
                creator_id=account.creator_id,
                connector_id=account.connector_id,
                account_id=account.id,
                capability=IntegrationCapability.CONTENT_PUBLISH,
                payload={"title": "Draft"},
                approved_by_user=True,
                approval_reference="approval-1",
                idempotency_key="idem-2",
            )
        )

        self.assertFalse(approval_required.success)
        self.assertEqual(approval_required.error.category, IntegrationErrorCategory.CONFLICT)
        self.assertEqual(approval_required.status, "approval_required")
        self.assertFalse(invalid_request.success)
        self.assertEqual(invalid_request.error.category, IntegrationErrorCategory.INVALID_REQUEST)
        self.assertTrue(write_one.success)
        self.assertIs(write_one, write_two)
        self.assertEqual(write_one.idempotency_key, "idem-2")

    def test_health_and_zero_account_fallback(self) -> None:
        service = _service()
        health = service.get_health(creator_id="creator-z")
        missing = service.get_health(creator_id="creator-z", account_id="missing")

        self.assertIn(health.status, {IntegrationHealthStatus.HEALTHY, IntegrationHealthStatus.DEGRADED})
        self.assertEqual(missing.status, IntegrationHealthStatus.UNKNOWN)
        self.assertEqual(service.list_accounts("creator-z"), ())

    def test_secret_safe_account_payload(self) -> None:
        service = _fake_service()
        account = service.link_account(
            IntegrationAccountLinkRequest(
                creator_id="creator-a",
                connector_id="fake.connector",
                external_account_id="acct-safe",
                display_name="Safe Account",
                credential_ref=None,
                metadata_summary={"hint": "safe"},
            )
        )
        payload = account.to_dict()

        self.assertTrue(str(account.credential_ref).startswith("integration.fake."))
        self.assertNotIn("access_token", payload)
        self.assertNotIn("refresh_token", payload)
        self.assertNotIn("client_secret", payload)
        self.assertEqual(payload["credential_ref"], account.credential_ref)

    def test_cli_list_and_accounts_surface(self) -> None:
        service = _fake_service()
        account = _linked_account(service)
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="entity", required=True)
        build_integrations_parser(subparsers)

        stdout = io.StringIO()
        stderr = io.StringIO()
        list_args = parser.parse_args(["integrations", "list", "--json"])
        code = handle_integrations_command(list_args, service=service, stdout=stdout, stderr=stderr)
        self.assertEqual(code, 0)
        self.assertGreaterEqual(json.loads(stdout.getvalue())["registered_connector_count"], 1)

        stdout = io.StringIO()
        accounts_args = parser.parse_args(["integrations", "accounts", "--creator-id", account.creator_id, "--json"])
        code = handle_integrations_command(accounts_args, service=service, stdout=stdout, stderr=stderr)
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(stdout.getvalue())), 1)

    def test_environment_diagnostic_includes_integration_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = AppSettings(
                application_name="Creator Intelligence Studio",
                environment="development",
                log_level="INFO",
                data_directory="data",
                logs_directory="logs",
                models_directory="models",
                artifacts_directory="artifacts",
                preferred_compute_backend="cuda",
                allow_cpu_basic_mode=True,
                external_ai_enabled=False,
            )
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = collect_environment_diagnostic(
                settings=settings,
                paths=paths,
                integration_summary={
                    "integration_contract_version": "integration-contract-v1",
                    "registered_connector_count": 3,
                    "registered_connector_ids": ["fake.connector", "local.connector", "youtube.connector"],
                    "connectors": [],
                },
            )

        self.assertEqual(diagnostic.integration_contract_version, "integration-contract-v1")
        self.assertEqual(diagnostic.registered_connector_count, 3)
        self.assertEqual(diagnostic.registered_connector_ids, ("fake.connector", "local.connector", "youtube.connector"))


if __name__ == "__main__":
    unittest.main()
