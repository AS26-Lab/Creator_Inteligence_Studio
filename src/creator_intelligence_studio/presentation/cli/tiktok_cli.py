"""CLI de la integracion de TikTok de solo lectura."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from creator_intelligence_studio.application.commands.tiktok_commands import (
    ConnectTikTokCommand,
    DisconnectTikTokConnectionCommand,
    ExportTikTokSyncReportCommand,
    ListTikTokConnectionsCommand,
    ListTikTokProfilesCommand,
    ListTikTokVideosCommand,
    RefreshTikTokVideoCommand,
    RevokeTikTokConnectionCommand,
    SelectTikTokProfileCommand,
    ShowTikTokConnectionCommand,
    ShowTikTokProfileCommand,
    ShowTikTokSyncRunCommand,
    ShowTikTokVideoCommand,
    SyncTikTokHistoryCommand,
    SyncTikTokIncrementalCommand,
    SyncTikTokProfileCommand,
    SyncTikTokRepairCommand,
    SyncTikTokResumeCommand,
    SyncTikTokVideosCommand,
    TikTokRateLimitCommand,
    LinkTikTokContentCommand,
    UnlinkTikTokContentCommand,
    VerifyTikTokConnectionCommand,
)
from creator_intelligence_studio.application.services.tiktok_integration_service import TikTokIntegrationService
from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokLinkMethod
from creator_intelligence_studio.domain.tiktok_integration.value_objects import READ_ONLY_SCOPES


def _json_default(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_tiktok_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("tiktok", help="Integracion oficial de solo lectura con TikTok")
    sub = parser.add_subparsers(dest="action", required=True)

    connections = sub.add_parser("connections", help="Listar conexiones")
    connections.add_argument("--creator-id", required=True)
    connections.add_argument("--json", action="store_true")

    connect = sub.add_parser("connect", help="Conectar una cuenta TikTok")
    connect.add_argument("--creator-id", required=True)
    connect.add_argument("--client-id", required=True)
    connect.add_argument("--client-secret")
    connect.add_argument("--authorization-code")
    connect.add_argument("--redirect-uri")
    connect.add_argument("--scopes-json")
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

    profiles = sub.add_parser("profiles", help="Listar perfiles")
    profiles.add_argument("--creator-id", required=True)
    profiles.add_argument("--json", action="store_true")

    profile_select = sub.add_parser("profile-select", help="Seleccionar perfil")
    profile_select.add_argument("--profile-id", required=True)
    profile_select.add_argument("--json", action="store_true")

    profile_show = sub.add_parser("profile-show", help="Mostrar perfil")
    profile_show.add_argument("--profile-id", required=True)
    profile_show.add_argument("--json", action="store_true")

    sync_profile = sub.add_parser("sync-profile", help="Sincronizar metadata de perfil")
    sync_profile.add_argument("--profile-id", required=True)
    sync_profile.add_argument("--cursor")
    sync_profile.add_argument("--json", action="store_true")

    sync_videos = sub.add_parser("sync-videos", help="Sincronizar catalogo de videos")
    sync_videos.add_argument("--profile-id", required=True)
    sync_videos.add_argument("--cursor")
    sync_videos.add_argument("--max-count", type=int, default=20)
    sync_videos.add_argument("--json", action="store_true")

    sync_incremental = sub.add_parser("sync-incremental", help="Sincronizacion incremental")
    sync_incremental.add_argument("--profile-id", required=True)
    sync_incremental.add_argument("--cursor")
    sync_incremental.add_argument("--max-count", type=int, default=20)
    sync_incremental.add_argument("--json", action="store_true")

    sync_resume = sub.add_parser("sync-resume", help="Reanudar una corrida")
    sync_resume.add_argument("--run-id", required=True)
    sync_resume.add_argument("--json", action="store_true")

    sync_repair = sub.add_parser("sync-repair", help="Reparar una sincronizacion")
    sync_repair.add_argument("--profile-id", required=True)
    sync_repair.add_argument("--json", action="store_true")

    sync_history = sub.add_parser("sync-history", help="Historial de corridas")
    sync_history.add_argument("--creator-id", required=True)
    sync_history.add_argument("--json", action="store_true")

    sync_show = sub.add_parser("sync-show", help="Mostrar una corrida")
    sync_show.add_argument("--run-id", required=True)
    sync_show.add_argument("--json", action="store_true")

    videos = sub.add_parser("videos", help="Listar videos remotos")
    videos.add_argument("--profile-id", required=True)
    videos.add_argument("--json", action="store_true")

    video_show = sub.add_parser("video-show", help="Mostrar video remoto")
    video_show.add_argument("--remote-video-id", required=True)
    video_show.add_argument("--json", action="store_true")

    video_refresh = sub.add_parser("video-refresh", help="Refrescar cover y metadata")
    video_refresh.add_argument("--remote-video-id", required=True)
    video_refresh.add_argument("--json", action="store_true")

    link = sub.add_parser("link-content", help="Vincular contenido remoto")
    link.add_argument("--remote-video-id", required=True)
    link.add_argument("--publication-id")
    link.add_argument("--video-asset-id")
    link.add_argument("--packaging-asset-id")
    link.add_argument("--link-method", default=TikTokLinkMethod.MANUAL.value, choices=[item.value for item in TikTokLinkMethod])
    link.add_argument("--confidence-level", default="low")
    link.add_argument("--status", default="pending")
    link.add_argument("--json", action="store_true")

    unlink = sub.add_parser("unlink-content", help="Desvincular contenido remoto")
    unlink.add_argument("--remote-video-id", required=True)
    unlink.add_argument("--json", action="store_true")

    rate_limit = sub.add_parser("rate-limit", help="Uso de rate limits")
    rate_limit.add_argument("--connection-id", required=True)
    rate_limit.add_argument("--json", action="store_true")

    export = sub.add_parser("export-report", help="Exportar reporte")
    export.add_argument("--run-id", required=True)
    export.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export.add_argument("--output")
    export.add_argument("--json", action="store_true")


def handle_tiktok(args: argparse.Namespace, *, service: TikTokIntegrationService, stdout=None, stderr=None) -> int:
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    if args.action == "connections":
        command = ListTikTokConnectionsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_connections(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) if args.json else "\n".join(item["id"] for item in payload), file=stdout)
        return 0
    if args.action == "connect":
        command = ConnectTikTokCommand(
            creator_id=args.creator_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
            authorization_code=args.authorization_code,
            redirect_uri=args.redirect_uri,
            scopes_json=args.scopes_json,
            account_identifier=args.account_identifier,
        )
        scopes = tuple(json.loads(command.scopes_json)) if command.scopes_json else READ_ONLY_SCOPES
        result = service.connect_account(
            creator_id=command.creator_id,
            client_id=command.client_id,
            client_secret=command.client_secret,
            authorization_code=command.authorization_code,
            redirect_uri=command.redirect_uri,
            scopes=scopes,
            account_identifier=command.account_identifier,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else (result.authorization_url or result.connection.id), file=stdout)
        return 0
    if args.action == "connection-show":
        command = ShowTikTokConnectionCommand(args.connection_id)
        payload = service.show_connection(command.connection_id)
        if payload is None:
            print("Conexion no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "verify":
        command = VerifyTikTokConnectionCommand(args.connection_id)
        payload = service.verify_connection(command.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "disconnect":
        command = DisconnectTikTokConnectionCommand(args.connection_id)
        payload = service.disconnect_connection(command.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "revoke":
        command = RevokeTikTokConnectionCommand(args.connection_id)
        payload = service.revoke_connection(command.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profiles":
        command = ListTikTokProfilesCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_profiles(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profile-select":
        command = SelectTikTokProfileCommand(args.profile_id)
        payload = service.select_profile(command.profile_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profile-show":
        command = ShowTikTokProfileCommand(args.profile_id)
        payload = service.show_profile(command.profile_id)
        if payload is None:
            print("Perfil no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-profile":
        command = SyncTikTokProfileCommand(args.profile_id, cursor=args.cursor)
        payload = service.sync_profile(profile_id=command.profile_id, cursor=command.cursor)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-videos":
        command = SyncTikTokVideosCommand(args.profile_id, cursor=args.cursor, max_count=args.max_count)
        payload = service.sync_videos(profile_id=command.profile_id, cursor=command.cursor, max_count=command.max_count)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-incremental":
        command = SyncTikTokIncrementalCommand(args.profile_id, cursor=args.cursor, max_count=args.max_count)
        payload = service.sync_incremental(profile_id=command.profile_id, cursor=command.cursor, max_count=command.max_count)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-resume":
        command = SyncTikTokResumeCommand(args.run_id)
        payload = service.resume_sync(command.run_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-repair":
        command = SyncTikTokRepairCommand(args.profile_id)
        payload = service.sync_repair(profile_id=command.profile_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-history":
        command = SyncTikTokHistoryCommand(args.creator_id)
        payload = [item.to_dict() for item in service.sync_history(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-show":
        command = ShowTikTokSyncRunCommand(args.run_id)
        payload = service.show_sync_run(command.run_id)
        if payload is None:
            print("Corrida no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "videos":
        command = ListTikTokVideosCommand(args.profile_id)
        payload = [item.to_dict() for item in service.list_remote_videos(command.profile_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "video-show":
        command = ShowTikTokVideoCommand(args.remote_video_id)
        payload = service.show_remote_video(command.remote_video_id)
        if payload is None:
            print("Video remoto no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "video-refresh":
        command = RefreshTikTokVideoCommand(args.remote_video_id)
        payload = service.sync_cover_refresh(remote_video_id=command.remote_video_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "link-content":
        command = LinkTikTokContentCommand(
            remote_video_id=args.remote_video_id,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            packaging_asset_id=args.packaging_asset_id,
            link_method=TikTokLinkMethod(args.link_method),
            confidence_level=args.confidence_level,
            status=args.status,
        )
        payload = service.link_content(
            remote_video_id=command.remote_video_id,
            publication_id=command.publication_id,
            video_asset_id=command.video_asset_id,
            packaging_asset_id=command.packaging_asset_id,
            link_method=command.link_method,
            confidence_level=command.confidence_level,
            status=command.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "unlink-content":
        command = UnlinkTikTokContentCommand(args.remote_video_id)
        payload = service.unlink_content(remote_video_id=command.remote_video_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "rate-limit":
        command = TikTokRateLimitCommand(args.connection_id)
        payload = [item.to_dict() for item in service.list_rate_limit_usage(command.connection_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-report":
        command = ExportTikTokSyncReportCommand(args.run_id, args.format, output=getattr(args, "output", None))
        destination = Path(command.output) if command.output else None
        path = service.export_report(command.run_id, command.format, destination=destination)
        print(json.dumps({"run_id": command.run_id, "format": command.format, "path": str(path)}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de tiktok no reconocida.")
