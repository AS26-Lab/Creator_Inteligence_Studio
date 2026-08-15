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

    youtube_parser = integrations_sub.add_parser("youtube", help="Conector YouTube read-first")
    youtube_sub = youtube_parser.add_subparsers(dest="youtube_action", required=True)

    youtube_auth_start = youtube_sub.add_parser("auth-start", help="Iniciar OAuth para YouTube")
    youtube_auth_start.add_argument("--creator-id", required=True)
    youtube_auth_start.add_argument("--client-id")
    youtube_auth_start.add_argument("--client-secret")
    youtube_auth_start.add_argument("--redirect-uri")
    youtube_auth_start.add_argument("--scopes-json")
    youtube_auth_start.add_argument("--json", action="store_true")

    youtube_auth_status = youtube_sub.add_parser("auth-status", help="Mostrar estado de autenticacion de YouTube")
    youtube_auth_status.add_argument("--creator-id", required=True)
    youtube_auth_status.add_argument("--account-id", required=True)
    youtube_auth_status.add_argument("--json", action="store_true")

    youtube_account = youtube_sub.add_parser("account", help="Leer perfil de cuenta autenticada")
    youtube_account.add_argument("--creator-id", required=True)
    youtube_account.add_argument("--account-id", required=True)
    youtube_account.add_argument("--json", action="store_true")

    youtube_videos = youtube_sub.add_parser("videos", help="Listar videos del creador")
    youtube_videos.add_argument("--creator-id", required=True)
    youtube_videos.add_argument("--account-id", required=True)
    youtube_videos.add_argument("--page-token")
    youtube_videos.add_argument("--max-results", type=int, default=10)
    youtube_videos.add_argument("--json", action="store_true")

    youtube_video = youtube_sub.add_parser("video", help="Leer metadatos de video")
    youtube_video.add_argument("--creator-id", required=True)
    youtube_video.add_argument("--account-id", required=True)
    youtube_video.add_argument("--video-id", required=True)
    youtube_video.add_argument("--json", action="store_true")

    youtube_analytics = youtube_sub.add_parser("analytics", help="Leer analiticas de YouTube")
    youtube_analytics.add_argument("--creator-id", required=True)
    youtube_analytics.add_argument("--account-id", required=True)
    youtube_analytics.add_argument("--start-date")
    youtube_analytics.add_argument("--end-date")
    youtube_analytics.add_argument("--video-id")
    youtube_analytics.add_argument("--metrics-json")
    youtube_analytics.add_argument("--dimensions-json")
    youtube_analytics.add_argument("--filters-json")
    youtube_analytics.add_argument("--max-results", type=int, default=200)
    youtube_analytics.add_argument("--json", action="store_true")

    youtube_disconnect = youtube_sub.add_parser("disconnect", help="Desconectar una cuenta de YouTube")
    youtube_disconnect.add_argument("--creator-id", required=True)
    youtube_disconnect.add_argument("--account-id", required=True)
    youtube_disconnect.add_argument("--json", action="store_true")


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


def _get_youtube_connector(service: IntegrationService):
    connector = service.registry.get("youtube.connector")
    if connector is None:
        raise DomainError("Conector de YouTube no registrado.")
    return connector


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
    if args.action == "youtube":
        connector = _get_youtube_connector(service)
        if args.youtube_action == "auth-start":
            scopes = _parse_string_list(args.scopes_json)
            result = connector.begin_authorization(
                creator_id=args.creator_id,
                client_id=args.client_id,
                client_secret=args.client_secret,
                redirect_uri=args.redirect_uri,
                scopes=scopes or None,
            )
            payload = result.to_dict()
            if args.json:
                print(_dump(payload), file=stdout)
            else:
                print(f"Authorization URL: {payload['authorization_url']}", file=stdout)
                print(f"State: {payload['state']}", file=stdout)
                print(f"Redirect URI: {payload['redirect_uri']}", file=stdout)
                print(f"Scopes: {payload['scopes']}", file=stdout)
            return 0
        if args.youtube_action == "auth-status":
            account = connector.get_account(args.account_id)
            health = connector.get_health(creator_id=args.creator_id, account_id=args.account_id)
            payload = {
                "account": None if account is None else account.to_dict(),
                "health": health.to_dict(),
                "creator_id": args.creator_id,
                "account_id": args.account_id,
            }
            print(_dump(payload), file=stdout)
            return 0
        if args.youtube_action == "account":
            request = IntegrationReadRequest(
                request_id="youtube-account-read",
                creator_id=args.creator_id,
                connector_id="youtube.connector",
                account_id=args.account_id,
                capability=IntegrationCapability.ACCOUNT_PROFILE_READ,
                timestamp=utc_now(),
            )
            result = service.read(request)
            print(_dump(result.to_dict()), file=stdout)
            return 0
        if args.youtube_action == "videos":
            request = IntegrationReadRequest(
                request_id="youtube-videos-read",
                creator_id=args.creator_id,
                connector_id="youtube.connector",
                account_id=args.account_id,
                capability=IntegrationCapability.CONTENT_LIST_READ,
                parameters={
                    "page_token": args.page_token,
                    "max_results": args.max_results,
                },
                timestamp=utc_now(),
            )
            result = service.read(request)
            print(_dump(result.to_dict()), file=stdout)
            return 0
        if args.youtube_action == "video":
            request = IntegrationReadRequest(
                request_id="youtube-video-read",
                creator_id=args.creator_id,
                connector_id="youtube.connector",
                account_id=args.account_id,
                capability=IntegrationCapability.CONTENT_METADATA_READ,
                parameters={"video_ids": [args.video_id]},
                timestamp=utc_now(),
            )
            result = service.read(request)
            print(_dump(result.to_dict()), file=stdout)
            return 0
        if args.youtube_action == "analytics":
            parameters: dict[str, object] = {
                "start_date": args.start_date,
                "end_date": args.end_date,
                "max_results": args.max_results,
            }
            if args.video_id:
                parameters["video_id"] = args.video_id
            metrics = _parse_string_list(args.metrics_json)
            dimensions = _parse_string_list(args.dimensions_json)
            filters = _parse_json_object(args.filters_json)
            if metrics:
                parameters["metrics"] = list(metrics)
            if dimensions:
                parameters["dimensions"] = list(dimensions)
            if filters:
                parameters["filters"] = filters
            request = IntegrationReadRequest(
                request_id="youtube-analytics-read",
                creator_id=args.creator_id,
                connector_id="youtube.connector",
                account_id=args.account_id,
                capability=IntegrationCapability.ANALYTICS_READ,
                parameters=parameters,
                timestamp=utc_now(),
            )
            result = service.read(request)
            print(_dump(result.to_dict()), file=stdout)
            return 0
        if args.youtube_action == "disconnect":
            result = connector.disconnect_account(creator_id=args.creator_id, account_id=args.account_id)
            payload = {"creator_id": args.creator_id, "account_id": args.account_id, "disconnected": result}
            print(_dump(payload), file=stdout)
            return 0
        raise DomainError("Accion de youtube no reconocida.")
    raise DomainError("Accion de integrations no reconocida.")
