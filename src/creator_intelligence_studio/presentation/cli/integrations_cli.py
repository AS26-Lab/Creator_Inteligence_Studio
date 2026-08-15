"""CLI technical surface for provider-neutral integrations."""

from __future__ import annotations

import argparse
import json
from typing import Any

from creator_intelligence_studio.application.services.integration_service import IntegrationService
from creator_intelligence_studio.domain.integrations import (
    IntegrationAccountLinkRequest,
    IntegrationAuthType,
    IntegrationCapability,
    IntegrationReadRequest,
    IntegrationWriteRequest,
)
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.shared.dates import utc_now


def _json_default(value: Any):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)


def build_integrations_parser(subparsers) -> None:
    parser = subparsers.add_parser("integrations", help="Fundacion de integraciones")
    integrations_sub = parser.add_subparsers(dest="action", required=True)

    list_parser = integrations_sub.add_parser("list", help="Listar conectores registrados")
    list_parser.add_argument("--json", action="store_true")

    capabilities_parser = integrations_sub.add_parser("capabilities", help="Mostrar capacidades de un conector")
    capabilities_parser.add_argument("--connector-id", required=True)
    capabilities_parser.add_argument("--json", action="store_true")

    accounts_parser = integrations_sub.add_parser("accounts", help="Listar cuentas vinculadas")
    accounts_parser.add_argument("--creator-id", required=True)
    accounts_parser.add_argument("--json", action="store_true")

    health_parser = integrations_sub.add_parser("health", help="Mostrar estado de integraciones")
    health_parser.add_argument("--creator-id", required=True)
    health_parser.add_argument("--account-id")
    health_parser.add_argument("--json", action="store_true")

    link_parser = integrations_sub.add_parser("link", help="Vincular una cuenta de integracion")
    link_parser.add_argument("--creator-id", required=True)
    link_parser.add_argument("--connector-id", required=True)
    link_parser.add_argument("--external-account-id", required=True)
    link_parser.add_argument("--display-name", required=True)
    link_parser.add_argument("--credential-ref")
    link_parser.add_argument("--granted-scopes-json")
    link_parser.add_argument("--granted-capabilities-json")
    link_parser.add_argument("--auth-type", default=IntegrationAuthType.LOCAL_NO_AUTH.value, choices=[item.value for item in IntegrationAuthType])
    link_parser.add_argument("--json", action="store_true")

    unlink_parser = integrations_sub.add_parser("unlink", help="Desvincular una cuenta de integracion")
    unlink_parser.add_argument("--creator-id", required=True)
    unlink_parser.add_argument("--account-id", required=True)
    unlink_parser.add_argument("--json", action="store_true")

    fake_read = integrations_sub.add_parser("fake-read", help="Lectura determinista contra el conector fake")
    fake_read.add_argument("--creator-id", required=True)
    fake_read.add_argument("--connector-id", default="fake.connector")
    fake_read.add_argument("--account-id", required=True)
    fake_read.add_argument("--capability", required=True, choices=[item.value for item in IntegrationCapability])
    fake_read.add_argument("--request-id", default="integration-read")
    fake_read.add_argument("--json", action="store_true")

    fake_write = integrations_sub.add_parser("fake-write", help="Escritura determinista contra el conector fake")
    fake_write.add_argument("--creator-id", required=True)
    fake_write.add_argument("--connector-id", default="fake.connector")
    fake_write.add_argument("--account-id", required=True)
    fake_write.add_argument("--capability", required=True, choices=[item.value for item in IntegrationCapability])
    fake_write.add_argument("--request-id", default="integration-write")
    fake_write.add_argument("--approval-reference")
    fake_write.add_argument("--approved-by-user", action="store_true")
    fake_write.add_argument("--idempotency-key", required=True)
    fake_write.add_argument("--payload-json")
    fake_write.add_argument("--json", action="store_true")


def _parse_capability(raw: str) -> IntegrationCapability:
    return IntegrationCapability(raw)


def _parse_json_object(raw: str | None) -> dict[str, object]:
    if raw is None:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("payload-json debe ser un objeto JSON.")
    return value


def _parse_string_list(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("El valor debe ser una lista JSON.")
    return tuple(str(item) for item in value)


def _parse_capability_list(raw: str | None) -> tuple[IntegrationCapability, ...]:
    if raw is None:
        return ()
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("El valor debe ser una lista JSON.")
    return tuple(IntegrationCapability(str(item)) for item in value)


def handle_integrations_command(args: argparse.Namespace, *, service: IntegrationService, stdout, stderr) -> int:
    if args.action == "list":
        payload = service.summary().to_dict()
        if args.json:
            print(_dump(payload), file=stdout)
        else:
            print(f"Contract: {payload['integration_contract_version']}", file=stdout)
            print(f"Connectors: {payload['registered_connector_count']}", file=stdout)
            for connector in payload["connector_summaries"]:
                definition = connector["definition"]
                health = connector["health"]
                print(
                    f"- {definition['connector_id']} | {definition['display_name']} | "
                    f"{definition['authentication_type']} | {health['status']}",
                    file=stdout,
                )
        return 0
    if args.action == "capabilities":
        connector = service.registry.get(args.connector_id)
        if connector is None:
            print("Conector no encontrado.", file=stderr)
            return 1
        payload = {
            "connector_id": args.connector_id,
            "definition": connector.definition.to_dict(),
        }
        if args.json:
            print(_dump(payload), file=stdout)
        else:
            print(f"Connector: {connector.definition.connector_id}", file=stdout)
            print(f"Capabilities: {[capability.value for capability in connector.definition.capabilities]}", file=stdout)
        return 0
    if args.action == "accounts":
        payload = [account.to_dict() for account in service.list_accounts(args.creator_id)]
        print(_dump(payload), file=stdout)
        return 0
    if args.action == "health":
        payload = service.get_health(creator_id=args.creator_id, account_id=args.account_id).to_dict()
        print(_dump(payload), file=stdout)
        return 0
    if args.action == "link":
        granted_scopes = _parse_string_list(args.granted_scopes_json)
        granted_capabilities = _parse_capability_list(args.granted_capabilities_json)
        request = IntegrationAccountLinkRequest(
            creator_id=args.creator_id,
            connector_id=args.connector_id,
            external_account_id=args.external_account_id,
            display_name=args.display_name,
            credential_ref=args.credential_ref,
            granted_scopes=granted_scopes,
            granted_capabilities=granted_capabilities,
            auth_type=IntegrationAuthType(args.auth_type),
            linked_at=utc_now(),
        )
        account = service.link_account(request)
        print(_dump(account.to_dict()), file=stdout)
        return 0
    if args.action == "unlink":
        result = service.unlink_account(creator_id=args.creator_id, account_id=args.account_id)
        print(_dump({"creator_id": args.creator_id, "account_id": args.account_id, "unlinked": result}), file=stdout)
        return 0
    if args.action == "fake-read":
        request = IntegrationReadRequest(
            request_id=args.request_id,
            creator_id=args.creator_id,
            connector_id=args.connector_id,
            account_id=args.account_id,
            capability=_parse_capability(args.capability),
            timestamp=utc_now(),
        )
        result = service.read(request)
        print(_dump(result.to_dict()), file=stdout)
        return 0
    if args.action == "fake-write":
        request = IntegrationWriteRequest(
            request_id=args.request_id,
            creator_id=args.creator_id,
            connector_id=args.connector_id,
            account_id=args.account_id,
            capability=_parse_capability(args.capability),
            payload=_parse_json_object(args.payload_json),
            approved_by_user=bool(args.approved_by_user),
            approval_reference=args.approval_reference,
            idempotency_key=args.idempotency_key,
            timestamp=utc_now(),
        )
        result = service.write(request)
        print(_dump(result.to_dict()), file=stdout)
        return 0
    raise DomainError("Accion de integrations no reconocida.")
