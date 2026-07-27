"""CLI consolidada para integraciones de plataforma."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from creator_intelligence_studio.application.commands.platform_integration_commands import (
    PlatformOverviewCommand,
    PlatformReportCommand,
    PlatformSyncCommand,
)
from creator_intelligence_studio.application.services.platform_integration_service import PlatformIntegrationService
from creator_intelligence_studio.domain.platform_integrations.connection_types import PlatformKind


def _json_default(value: Any):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _serialize(items: Any, as_json: bool) -> str:
    if as_json:
        return json.dumps(items, ensure_ascii=False, indent=2, default=_json_default)
    return "\n".join(str(item) for item in items)


def build_platforms_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("platforms", help="Integraciones unificadas de plataforma")
    parser_sub = parser.add_subparsers(dest="action", required=True)

    overview = parser_sub.add_parser("overview", help="Resumen por plataforma")
    overview.add_argument("--creator-id", required=True)
    overview.add_argument("--json", action="store_true")

    connections = parser_sub.add_parser("connections", help="Listar conexiones")
    connections.add_argument("--creator-id", required=True)
    connections.add_argument("--json", action="store_true")

    connection_show = parser_sub.add_parser("connection-show", help="Mostrar una conexion")
    connection_show.add_argument("--platform", required=True, choices=[item.value for item in PlatformKind])
    connection_show.add_argument("--connection-id", required=True)
    connection_show.add_argument("--json", action="store_true")

    verify = parser_sub.add_parser("verify", help="Verificar conexiones")
    verify.add_argument("--creator-id", required=True)
    verify.add_argument("--platform", action="append", choices=[item.value for item in PlatformKind])
    verify.add_argument("--json", action="store_true")

    health = parser_sub.add_parser("health", help="Salud consolidada")
    health.add_argument("--creator-id", required=True)
    health.add_argument("--json", action="store_true")

    health_refresh = parser_sub.add_parser("health-refresh", help="Refrescar salud")
    health_refresh.add_argument("--creator-id", required=True)
    health_refresh.add_argument("--remote", action="store_true")
    health_refresh.add_argument("--json", action="store_true")

    capabilities = parser_sub.add_parser("capabilities", help="Matriz de capacidades")
    capabilities.add_argument("--creator-id", required=True)
    capabilities.add_argument("--json", action="store_true")

    data_availability = parser_sub.add_parser("data-availability", help="Disponibilidad de datos")
    data_availability.add_argument("--creator-id", required=True)
    data_availability.add_argument("--json", action="store_true")

    manual_import_status = parser_sub.add_parser("manual-import-status", help="Estado de importacion manual")
    manual_import_status.add_argument("--creator-id", required=True)
    manual_import_status.add_argument("--json", action="store_true")

    schedules = parser_sub.add_parser("schedules", help="Schedules consolidados")
    schedules.add_argument("--creator-id", required=True)
    schedules.add_argument("--json", action="store_true")

    sync = parser_sub.add_parser("sync", help="Sincronizar plataformas")
    sync.add_argument("--creator-id", required=True)
    sync.add_argument("--platform", action="append", choices=[item.value for item in PlatformKind])
    sync.add_argument("--all", action="store_true")
    sync.add_argument("--mode", default="sequential", choices=["sequential", "limited_parallel", "platform_ordered"])
    sync.add_argument("--incremental", action="store_true", default=True)
    sync.add_argument("--json", action="store_true")

    sync_show = parser_sub.add_parser("sync-show", help="Mostrar un grupo de sync")
    sync_show.add_argument("--group-id", required=True)
    sync_show.add_argument("--json", action="store_true")

    sync_history = parser_sub.add_parser("sync-history", help="Historial de sync")
    sync_history.add_argument("--creator-id", required=True)
    sync_history.add_argument("--json", action="store_true")

    sync_resume = parser_sub.add_parser("sync-resume", help="Reanudar grupo")
    sync_resume.add_argument("--group-id", required=True)
    sync_resume.add_argument("--json", action="store_true")

    sync_retry_failed = parser_sub.add_parser("sync-retry-failed", help="Reintentar solo fallidas")
    sync_retry_failed.add_argument("--group-id", required=True)
    sync_retry_failed.add_argument("--json", action="store_true")

    sync_cancel = parser_sub.add_parser("sync-cancel", help="Cancelar grupo")
    sync_cancel.add_argument("--group-id", required=True)
    sync_cancel.add_argument("--json", action="store_true")

    report = parser_sub.add_parser("report", help="Generar reporte")
    report.add_argument("--creator-id", required=True)
    report.add_argument("--type", required=True)
    report.add_argument("--json", action="store_true")

    export_report = parser_sub.add_parser("export-report", help="Exportar reporte")
    export_report.add_argument("--report-id", required=True)
    export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export_report.add_argument("--json", action="store_true")


def handle_platforms_command(args: argparse.Namespace, service: PlatformIntegrationService, stdout, stderr) -> int:
    if args.action == "overview":
        command = PlatformOverviewCommand(args.creator_id)
        payload = [row.to_dict() for row in service.build_overview(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "connections":
        payload = [item.to_dict() for item in service.list_connections(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "connection-show":
        payload = service.get_connection(args.connection_id)
        if payload is None:
            print("Conexion no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "verify":
        payload = []
        platforms = args.platform or [item.value for item in PlatformKind if item != PlatformKind.MANUAL_OTHER]
        for platform in platforms:
            for connection in service.list_connections(args.creator_id):
                if connection.platform.value == platform:
                    result = service.verify_connection(connection.id)
                    payload.append({"platform": platform, "connection_id": connection.id, "result": getattr(result, "to_dict", lambda: result)() if result is not None else None})
                    break
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "health":
        payload = [item.to_dict() for item in service.list_health_checks(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "health-refresh":
        payload = [item.to_dict() for item in service.list_health_checks(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "capabilities":
        payload = [item.to_dict() for item in service.list_capabilities(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "data-availability":
        payload = [item.to_dict() for item in service.list_data_availability(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "manual-import-status":
        payload = [item.to_dict() for item in service.list_manual_import_status(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "schedules":
        payload = [item.to_dict() for item in service.list_schedule_registry(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync":
        platforms = [PlatformKind(item) for item in args.platform] if args.platform else None
        if args.all or platforms is None:
            platforms = [PlatformKind.YOUTUBE, PlatformKind.INSTAGRAM, PlatformKind.TIKTOK, PlatformKind.MANUAL_OTHER]
        command = PlatformSyncCommand(args.creator_id, tuple(item.value for item in platforms), mode=args.mode, incremental=args.incremental)
        result = service.start_sync(creator_id=command.creator_id, platforms=list(command.platforms), mode=command.mode, incremental=command.incremental)
        print(json.dumps({"group": result.group.to_dict(), "items": [item.to_dict() for item in result.items], "warnings": result.warnings, "errors": result.errors}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-show":
        group = service.repository.get_platform_sync_group(args.group_id)
        if group is None:
            print("Grupo no encontrado.", file=stderr)
            return 1
        payload = {"group": group.to_dict(), "items": [item.to_dict() for item in service.list_sync_group_items(args.group_id)]}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-history":
        payload = [group.to_dict() for group in service.list_sync_groups(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-resume":
        payload = service.resume_sync(args.group_id)
        if payload is None:
            print("Grupo no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-retry-failed":
        payload = service.resume_sync(args.group_id)
        if payload is None:
            print("Grupo no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-cancel":
        payload = service.cancel_sync(args.group_id)
        if payload is None:
            print("Grupo no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "report":
        command = PlatformReportCommand(args.creator_id, args.type)
        report = service.build_report(command.creator_id, command.report_type)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-report":
        destination = service.export_report(args.report_id, args.format)
        payload = {"report_id": args.report_id, "format": args.format, "destination": None if destination is None else str(destination)}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de platforms no reconocida.")
