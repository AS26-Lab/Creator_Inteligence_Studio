"""CLI de la integracion de Instagram."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from creator_intelligence_studio.application.commands.instagram_commands import (
    ConnectInstagramCommand,
    DisconnectInstagramConnectionCommand,
    ExportInstagramSyncReportCommand,
    InstagramRateLimitCommand,
    LinkInstagramContentCommand,
    ListInstagramAccountsCommand,
    ListInstagramConnectionsCommand,
    ListInstagramMediaCommand,
    RevokeInstagramConnectionCommand,
    ResumeInstagramSyncCommand,
    SelectInstagramAccountCommand,
    ShowInstagramAccountCommand,
    ShowInstagramConnectionCommand,
    ShowInstagramMediaCommand,
    ShowInstagramSyncRunCommand,
    SyncInstagramAccountCommand,
    SyncInstagramHistoryCommand,
    SyncInstagramIncrementalCommand,
    SyncInstagramInsightsCommand,
    SyncInstagramMediaCommand,
    SyncInstagramRepairCommand,
    UnlinkInstagramContentCommand,
    VerifyInstagramConnectionCommand,
)
from creator_intelligence_studio.application.services.instagram_integration_service import InstagramIntegrationService
from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider, InstagramLinkMethod
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod
from creator_intelligence_studio.domain.instagram_integration.value_objects import READ_ONLY_SCOPES


def _json_default(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_instagram_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("instagram", help="Integracion de solo lectura con Instagram")
    sub = parser.add_subparsers(dest="action", required=True)

    connections = sub.add_parser("connections", help="Listar conexiones")
    connections.add_argument("--creator-id", required=True)
    connections.add_argument("--json", action="store_true")

    connect = sub.add_parser("connect", help="Conectar una cuenta profesional")
    connect.add_argument("--creator-id", required=True)
    connect.add_argument("--client-id", required=True)
    connect.add_argument("--client-secret")
    connect.add_argument("--authorization-code")
    connect.add_argument("--redirect-uri")
    connect.add_argument("--scopes-json")
    connect.add_argument("--provider", default=InstagramAuthProvider.INSTAGRAM_LOGIN.value, choices=[item.value for item in InstagramAuthProvider])
    connect.add_argument("--account-identifier")
    connect.add_argument("--json", action="store_true")

    connection_show = sub.add_parser("connection-show", help="Mostrar una conexion")
    connection_show.add_argument("--connection-id", required=True)
    connection_show.add_argument("--json", action="store_true")

    verify = sub.add_parser("verify", help="Verificar una conexion")
    verify.add_argument("--connection-id", required=True)
    verify.add_argument("--json", action="store_true")

    disconnect = sub.add_parser("disconnect", help="Desconectar localmente")
    disconnect.add_argument("--connection-id", required=True)
    disconnect.add_argument("--json", action="store_true")

    revoke = sub.add_parser("revoke", help="Revocar credenciales")
    revoke.add_argument("--connection-id", required=True)
    revoke.add_argument("--json", action="store_true")

    accounts = sub.add_parser("accounts", help="Listar cuentas")
    accounts.add_argument("--creator-id", required=True)
    accounts.add_argument("--json", action="store_true")

    account_select = sub.add_parser("account-select", help="Seleccionar una cuenta")
    account_select.add_argument("--account-id", required=True)
    account_select.add_argument("--json", action="store_true")

    account_show = sub.add_parser("account-show", help="Mostrar una cuenta")
    account_show.add_argument("--account-id", required=True)
    account_show.add_argument("--json", action="store_true")

    sync_account = sub.add_parser("sync-account", help="Sincronizar cuenta")
    sync_account.add_argument("--account-id", required=True)
    sync_account.add_argument("--cursor")
    sync_account.add_argument("--full-resync", action="store_true")
    sync_account.add_argument("--json", action="store_true")

    sync_media = sub.add_parser("sync-media", help="Sincronizar medios")
    sync_media.add_argument("--account-id", required=True)
    sync_media.add_argument("--cursor")
    sync_media.add_argument("--limit", type=int, default=25)
    sync_media.add_argument("--json", action="store_true")

    sync_insights = sub.add_parser("sync-insights", help="Sincronizar insights")
    sync_insights.add_argument("--account-id", required=True)
    sync_insights.add_argument("--remote-media-id")
    sync_insights.add_argument("--period", default=InstagramInsightPeriod.DAYS_28.value, choices=[item.value for item in InstagramInsightPeriod])
    sync_insights.add_argument("--json", action="store_true")

    sync_incremental = sub.add_parser("sync-incremental", help="Sincronizacion incremental")
    sync_incremental.add_argument("--account-id", required=True)
    sync_incremental.add_argument("--cursor")
    sync_incremental.add_argument("--json", action="store_true")

    sync_resume = sub.add_parser("sync-resume", help="Reanudar una corrida")
    sync_resume.add_argument("--run-id", required=True)
    sync_resume.add_argument("--json", action="store_true")

    sync_repair = sub.add_parser("sync-repair", help="Reparar sincronizacion")
    sync_repair.add_argument("--account-id", required=True)
    sync_repair.add_argument("--json", action="store_true")

    sync_history = sub.add_parser("sync-history", help="Historial de corridas")
    sync_history.add_argument("--creator-id", required=True)
    sync_history.add_argument("--json", action="store_true")

    sync_show = sub.add_parser("sync-show", help="Mostrar una corrida")
    sync_show.add_argument("--run-id", required=True)
    sync_show.add_argument("--json", action="store_true")

    media = sub.add_parser("media", help="Listar medios remotos")
    media.add_argument("--account-id", required=True)
    media.add_argument("--json", action="store_true")

    media_show = sub.add_parser("media-show", help="Mostrar medio remoto")
    media_show.add_argument("--remote-media-id", required=True)
    media_show.add_argument("--json", action="store_true")

    link = sub.add_parser("link-content", help="Vincular contenido remoto")
    link.add_argument("--remote-media-id", required=True)
    link.add_argument("--publication-id")
    link.add_argument("--video-asset-id")
    link.add_argument("--packaging-asset-id")
    link.add_argument("--link-method", default=InstagramLinkMethod.MANUAL.value, choices=[item.value for item in InstagramLinkMethod])
    link.add_argument("--confidence-level", default="low")
    link.add_argument("--status", default="pending")
    link.add_argument("--json", action="store_true")

    unlink = sub.add_parser("unlink-content", help="Desvincular contenido remoto")
    unlink.add_argument("--remote-media-id", required=True)
    unlink.add_argument("--json", action="store_true")

    rate_limit = sub.add_parser("rate-limit", help="Mostrar uso estimado de rate limits")
    rate_limit.add_argument("--connection-id", required=True)
    rate_limit.add_argument("--json", action="store_true")

    export = sub.add_parser("export-report", help="Exportar un reporte")
    export.add_argument("--run-id", required=True)
    export.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export.add_argument("--output")
    export.add_argument("--json", action="store_true")


def handle_instagram(args: argparse.Namespace, *, service: InstagramIntegrationService, stdout=None, stderr=None) -> int:
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    if args.action == "connections":
        payload = [item.to_dict() for item in service.list_connections(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) if args.json else "\n".join(item["id"] for item in payload), file=stdout)
        return 0
    if args.action == "connect":
        scopes = tuple(json.loads(args.scopes_json)) if args.scopes_json else READ_ONLY_SCOPES
        result = service.connect_account(
            creator_id=args.creator_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            authorization_code=args.authorization_code,
            redirect_uri=args.redirect_uri,
            scopes=scopes or tuple(),
            provider=InstagramAuthProvider(args.provider),
            account_identifier=args.account_identifier,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else (result.authorization_url or result.connection.id), file=stdout)
        return 0
    if args.action == "connection-show":
        payload = service.show_connection(args.connection_id)
        if payload is None:
            print("Conexion no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else json.dumps(payload.to_dict(), ensure_ascii=False, default=_json_default), file=stdout)
        return 0
    if args.action == "verify":
        payload = service.verify_connection(args.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "disconnect":
        payload = service.disconnect_connection(args.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "revoke":
        payload = service.revoke_connection(args.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "accounts":
        payload = [item.to_dict() for item in service.list_accounts(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "account-select":
        payload = service.select_account(args.account_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "account-show":
        payload = service.show_account(args.account_id)
        if payload is None:
            print("Cuenta no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-account":
        payload = service.sync_account(account_id=args.account_id, cursor=args.cursor, full_resync=bool(args.full_resync))
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-media":
        payload = service.sync_media(account_id=args.account_id, cursor=args.cursor, limit=args.limit)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-insights":
        payload = service.sync_insights(account_id=args.account_id, remote_media_id=args.remote_media_id, period=InstagramInsightPeriod(args.period))
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-incremental":
        payload = service.sync_incremental(account_id=args.account_id, cursor=args.cursor)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-resume":
        payload = service.resume_sync(args.run_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-repair":
        payload = service.sync_repair(account_id=args.account_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-history":
        payload = [item.to_dict() for item in service.list_sync_runs(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-show":
        payload = service.show_sync_run(args.run_id)
        if payload is None:
            print("Corrida no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "media":
        payload = [item.to_dict() for item in service.list_media(args.account_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "media-show":
        payload = service.show_media(args.remote_media_id)
        if payload is None:
            print("Medio remoto no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "link-content":
        payload = service.link_content(
            remote_media_id=args.remote_media_id,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            packaging_asset_id=args.packaging_asset_id,
            link_method=InstagramLinkMethod(args.link_method),
            confidence_level=args.confidence_level,
            status=args.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "unlink-content":
        payload = service.unlink_content(remote_media_id=args.remote_media_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "rate-limit":
        payload = [item.to_dict() for item in service.list_rate_limit_usage(args.connection_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-report":
        output = service.export_report(args.run_id, args.format, destination=Path(args.output) if args.output else None)
        print(json.dumps({"path": str(output)}, ensure_ascii=False, indent=2), file=stdout)
        return 0
    print("Accion de instagram no reconocida.", file=stderr)
    return 1
