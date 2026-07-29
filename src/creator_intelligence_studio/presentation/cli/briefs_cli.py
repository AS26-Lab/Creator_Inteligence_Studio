"""CLI para Content Brief and Pre-Production Foundation."""

from __future__ import annotations

import json
from typing import Any

from creator_intelligence_studio.application.commands.content_brief_commands import (
    CreateBriefRequestCommand,
    GenerateBriefCommand,
    ReviewBriefCommand,
    VersionBriefCommand,
)
from creator_intelligence_studio.application.services.content_brief_service import ContentBriefService
from creator_intelligence_studio.domain.content_briefs.errors import ContentBriefNotFoundError


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)


def build_briefs_parser(subparsers) -> None:
    parser = subparsers.add_parser("briefs", help="Content Briefs")
    briefs_sub = parser.add_subparsers(dest="action", required=True)

    overview = briefs_sub.add_parser("overview", help="Resumen de briefs")
    overview.add_argument("--creator-id", required=True)
    overview.add_argument("--json", action="store_true")

    requests = briefs_sub.add_parser("requests", help="Listar solicitudes")
    requests.add_argument("--creator-id", required=True)
    requests.add_argument("--json", action="store_true")

    request_create = briefs_sub.add_parser("request-create", help="Crear solicitud")
    request_create.add_argument("--creator-id", required=True)
    request_create.add_argument("--source-type", required=True)
    request_create.add_argument("--source-id")
    request_create.add_argument("--request-type")
    request_create.add_argument("--platform", action="append")
    request_create.add_argument("--content-type", action="append")
    request_create.add_argument("--objective", action="append")
    request_create.add_argument("--constraints-json", default="[]")
    request_create.add_argument("--preferences-json", default="{}")
    request_create.add_argument("--json", action="store_true")

    request_show = briefs_sub.add_parser("request-show", help="Mostrar solicitud")
    request_show.add_argument("--request-id", required=True)
    request_show.add_argument("--json", action="store_true")

    generate = briefs_sub.add_parser("generate", help="Generar brief")
    generate.add_argument("--request-id")
    generate.add_argument("--creator-id")
    generate.add_argument("--source-type")
    generate.add_argument("--source-id")
    generate.add_argument("--request-type")
    generate.add_argument("--platform", action="append")
    generate.add_argument("--content-type", action="append")
    generate.add_argument("--objective", action="append")
    generate.add_argument("--constraints-json", default="[]")
    generate.add_argument("--preferences-json", default="{}")
    generate.add_argument("--json", action="store_true")

    runs = briefs_sub.add_parser("runs", help="Corridas de briefs")
    runs.add_argument("--creator-id", required=True)
    runs.add_argument("--json", action="store_true")

    run_show = briefs_sub.add_parser("run-show", help="Mostrar corrida")
    run_show.add_argument("--run-id", required=True)
    run_show.add_argument("--json", action="store_true")

    run_cancel = briefs_sub.add_parser("run-cancel", help="Cancelar corrida")
    run_cancel.add_argument("--run-id", required=True)
    run_cancel.add_argument("--json", action="store_true")

    run_resume = briefs_sub.add_parser("run-resume", help="Reanudar corrida")
    run_resume.add_argument("--run-id", required=True)
    run_resume.add_argument("--json", action="store_true")

    list_parser = briefs_sub.add_parser("list", help="Listar briefs")
    list_parser.add_argument("--creator-id", required=True)
    list_parser.add_argument("--status")
    list_parser.add_argument("--platform")
    list_parser.add_argument("--json", action="store_true")

    show = briefs_sub.add_parser("show", help="Mostrar brief")
    show.add_argument("--brief-id", required=True)
    show.add_argument("--json", action="store_true")

    context = briefs_sub.add_parser("context", help="Contexto del brief")
    context.add_argument("--brief-id", required=True)
    context.add_argument("--json", action="store_true")

    for action in ("sections", "audience", "promises", "angles", "messages", "hooks", "outline", "talking-points", "claims", "fact-checks", "packaging", "visual", "audio", "adaptations", "boundaries", "references", "rights", "assets", "requirements", "shots", "checklists", "gates", "readiness", "risks", "dependencies"):
        sub = briefs_sub.add_parser(action, help=action.replace("-", " "))
        sub.add_argument("--brief-id", required=True)
        sub.add_argument("--json", action="store_true")

    review = briefs_sub.add_parser("review", help="Revisar brief")
    review.add_argument("--brief-id", required=True)
    review.add_argument("--decision", required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--reviewer")
    review.add_argument("--json", action="store_true")

    version_create = briefs_sub.add_parser("version-create", help="Crear version")
    version_create.add_argument("--brief-id", required=True)
    version_create.add_argument("--reason", default="versioned_brief")
    version_create.add_argument("--json", action="store_true")

    supersede = briefs_sub.add_parser("supersede", help="Superseder brief")
    supersede.add_argument("--brief-id", required=True)
    supersede.add_argument("--replacement-id")
    supersede.add_argument("--reason", required=True)
    supersede.add_argument("--json", action="store_true")

    snapshot_create = briefs_sub.add_parser("snapshot-create", help="Crear snapshot")
    snapshot_create.add_argument("--brief-id", required=True)
    snapshot_create.add_argument("--snapshot-type", default="draft_brief")
    snapshot_create.add_argument("--json", action="store_true")

    snapshots = briefs_sub.add_parser("snapshots", help="Listar snapshots")
    snapshots.add_argument("--brief-id", required=True)
    snapshots.add_argument("--json", action="store_true")

    snapshot_compare = briefs_sub.add_parser("snapshot-compare", help="Comparar snapshots")
    snapshot_compare.add_argument("--left-id", required=True)
    snapshot_compare.add_argument("--right-id", required=True)
    snapshot_compare.add_argument("--json", action="store_true")

    report = briefs_sub.add_parser("report", help="Generar reporte")
    report.add_argument("--brief-id")
    report.add_argument("--creator-id", required=True)
    report.add_argument("--type", required=True, dest="report_type")
    report.add_argument("--json", action="store_true")

    export_report = briefs_sub.add_parser("export-report", help="Exportar reporte")
    export_report.add_argument("--report-id", required=True)
    export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export_report.add_argument("--json", action="store_true")


def handle_briefs_command(args, *, service: ContentBriefService, stdout, stderr) -> int:
    if args.action == "overview":
        payload = service.build_overview(args.creator_id)
        print(_dump(payload), file=stdout)
        return 0
    if args.action == "requests":
        print(_dump([item.to_dict() for item in service.list_requests(args.creator_id)]), file=stdout)
        return 0
    if args.action == "request-create":
        command = CreateBriefRequestCommand(args.creator_id, args.source_type, args.source_id, args.request_type)
        payload = service.create_request(
            creator_id=command.creator_id,
            source_type=command.source_type,
            source_id=command.source_id,
            request_type=command.request_type,
            platform_scope_json=json.dumps(args.platform or [], ensure_ascii=False),
            content_type_scope_json=json.dumps(args.content_type or [], ensure_ascii=False),
            objective_scope_json=json.dumps(args.objective or [], ensure_ascii=False),
            constraints_json=args.constraints_json,
            preferences_json=args.preferences_json,
        )
        print(_dump(payload.to_dict()), file=stdout)
        return 0
    if args.action == "request-show":
        request = service.get_request(args.request_id)
        if request is None:
            raise ContentBriefNotFoundError("La solicitud no existe.")
        print(_dump(request.to_dict()), file=stdout)
        return 0
    if args.action == "generate":
        command = GenerateBriefCommand(args.request_id, args.creator_id, args.source_type, args.source_id)
        payload = service.generate_brief(
            request_id=command.request_id,
            creator_id=command.creator_id,
            source_type=command.source_type,
            source_id=command.source_id,
            request_type=args.request_type,
            platform_scope_json=json.dumps(args.platform or [], ensure_ascii=False),
            content_type_scope_json=json.dumps(args.content_type or [], ensure_ascii=False),
            objective_scope_json=json.dumps(args.objective or [], ensure_ascii=False),
            constraints_json=args.constraints_json,
            preferences_json=args.preferences_json,
        )
        print(_dump(payload.to_dict()), file=stdout)
        return 0
    if args.action == "runs":
        print(_dump([item.to_dict() for item in service.list_tasks(args.creator_id)]), file=stdout)
        return 0
    if args.action == "run-show":
        request = service.get_request(args.run_id)
        creator_id = request.creator_id if request is not None else None
        task = None
        if creator_id is not None:
            task = next((item for item in service.list_tasks(creator_id) if item.id == args.run_id), None)
        if task is None and request is not None:
            task = next((item for item in service.list_tasks(request.creator_id) if item.id == request.id), None)
        print(_dump(None if task is None else task.to_dict()), file=stdout)
        return 0
    if args.action == "run-cancel":
        print(_dump(service.cancel_run(args.run_id).to_dict()), file=stdout)
        return 0
    if args.action == "run-resume":
        print(_dump(service.resume_run(args.run_id).to_dict()), file=stdout)
        return 0
    if args.action == "list":
        briefs = service.list_briefs(args.creator_id)
        if args.status:
            briefs = [brief for brief in briefs if brief.status.value == args.status]
        if args.platform:
            briefs = [brief for brief in briefs if args.platform in str(brief.platform_scope_json)]
        print(_dump([brief.to_dict() for brief in briefs]), file=stdout)
        return 0
    if args.action == "show":
        brief = service.get_brief(args.brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        print(_dump(brief.to_dict()), file=stdout)
        return 0
    if args.action == "context":
        brief = service.get_brief(args.brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        context = service.get_context_snapshot(brief.context_snapshot_id)
        print(_dump(None if context is None else context.to_dict()), file=stdout)
        return 0
    if args.action == "sections":
        print(_dump([item.to_dict() for item in service.list_sections(args.brief_id)]), file=stdout)
        return 0
    if args.action == "audience":
        print(_dump([item.to_dict() for item in service.list_audience_definitions(args.brief_id)]), file=stdout)
        return 0
    if args.action == "promises":
        print(_dump([item.to_dict() for item in service.list_promises(args.brief_id)]), file=stdout)
        return 0
    if args.action == "angles":
        print(_dump([item.to_dict() for item in service.list_angles(args.brief_id)]), file=stdout)
        return 0
    if args.action == "messages":
        print(_dump([item.to_dict() for item in service.list_message_hierarchy(args.brief_id)]), file=stdout)
        return 0
    if args.action == "hooks":
        print(_dump([item.to_dict() for item in service.list_hooks(args.brief_id)]), file=stdout)
        return 0
    if args.action == "outline":
        print(_dump([item.to_dict() for item in service.list_outlines(args.brief_id)]), file=stdout)
        return 0
    if args.action == "talking-points":
        print(_dump([item.to_dict() for item in service.list_talking_points(args.brief_id)]), file=stdout)
        return 0
    if args.action == "claims":
        print(_dump([item.to_dict() for item in service.list_claims(args.brief_id)]), file=stdout)
        return 0
    if args.action == "fact-checks":
        print(_dump([item.to_dict() for item in service.list_fact_checks(args.brief_id)]), file=stdout)
        return 0
    if args.action == "packaging":
        print(_dump([item.to_dict() for item in service.list_packaging(args.brief_id)]), file=stdout)
        return 0
    if args.action == "visual":
        print(_dump([item.to_dict() for item in service.list_visual(args.brief_id)]), file=stdout)
        return 0
    if args.action == "audio":
        print(_dump([item.to_dict() for item in service.list_audio(args.brief_id)]), file=stdout)
        return 0
    if args.action == "adaptations":
        print(_dump([item.to_dict() for item in service.list_adaptations(args.brief_id)]), file=stdout)
        return 0
    if args.action == "boundaries":
        print(_dump([item.to_dict() for item in service.list_boundaries(args.brief_id)]), file=stdout)
        return 0
    if args.action == "references":
        print(_dump([item.to_dict() for item in service.list_references(args.brief_id)]), file=stdout)
        return 0
    if args.action == "rights":
        print(_dump([item.to_dict() for item in service.list_rights(args.brief_id)]), file=stdout)
        return 0
    if args.action == "assets":
        print(_dump([item.to_dict() for item in service.list_assets(args.brief_id)]), file=stdout)
        return 0
    if args.action == "requirements":
        print(_dump([item.to_dict() for item in service.list_requirements(args.brief_id)]), file=stdout)
        return 0
    if args.action == "shots":
        print(_dump([item.to_dict() for item in service.list_shots(args.brief_id)]), file=stdout)
        return 0
    if args.action == "checklists":
        print(_dump([item.to_dict() for item in service.list_checklists(args.brief_id)]), file=stdout)
        return 0
    if args.action == "gates":
        print(_dump([item.to_dict() for item in service.list_gates(args.brief_id)]), file=stdout)
        return 0
    if args.action == "readiness":
        print(_dump(service.calculate_readiness(args.brief_id)), file=stdout)
        return 0
    if args.action == "risks":
        print(_dump([item.to_dict() for item in service.list_risks(args.brief_id)]), file=stdout)
        return 0
    if args.action == "dependencies":
        print(_dump([item.to_dict() for item in service.list_dependencies(args.brief_id)]), file=stdout)
        return 0
    if args.action == "review":
        command = ReviewBriefCommand(args.brief_id, args.decision, args.reason)
        payload = service.review_brief(command.brief_id, decision=command.decision, reason=command.reason, reviewer=args.reviewer)
        print(_dump(payload.to_dict()), file=stdout)
        return 0
    if args.action == "version-create":
        command = VersionBriefCommand(args.brief_id, args.reason)
        print(_dump(service.version_brief(command.brief_id, reason=command.reason).to_dict()), file=stdout)
        return 0
    if args.action == "supersede":
        print(_dump(service.supersede_brief(args.brief_id, replacement_id=args.replacement_id, reason=args.reason).to_dict()), file=stdout)
        return 0
    if args.action == "snapshot-create":
        print(_dump(service.create_snapshot(args.brief_id, snapshot_type=args.snapshot_type).to_dict()), file=stdout)
        return 0
    if args.action == "snapshots":
        print(_dump([item.to_dict() for item in service.list_snapshots(args.brief_id)]), file=stdout)
        return 0
    if args.action == "snapshot-compare":
        print(_dump(service.compare_snapshots(args.left_id, args.right_id)), file=stdout)
        return 0
    if args.action == "report":
        print(_dump(service.build_report(content_brief_id=args.brief_id, creator_id=args.creator_id, report_type=args.report_type).to_dict()), file=stdout)
        return 0
    if args.action == "export-report":
        path = service.export_report(args.report_id, args.format)
        print(_dump({"path": str(path)}), file=stdout)
        return 0
    raise ValueError("Comando de briefs no reconocido.")
