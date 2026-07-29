"""CLI para Script Outline and Production Preparation Foundation."""

from __future__ import annotations

import json
from typing import Any

from creator_intelligence_studio.application.commands.production_preparation_commands import (
    CreateProductionRequestCommand,
    GenerateOutlineCommand,
    ReviewOutlineCommand,
    VersionOutlineCommand,
)
from creator_intelligence_studio.application.services.production_preparation_service import ProductionPreparationService
from creator_intelligence_studio.domain.production_preparation.errors import ProductionPreparationNotFoundError


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


def build_production_parser(subparsers) -> None:
    parser = subparsers.add_parser("production", help="Production Preparation")
    production_sub = parser.add_subparsers(dest="action", required=True)

    overview = production_sub.add_parser("overview", help="Resumen de produccion")
    overview.add_argument("--creator-id", required=True)
    overview.add_argument("--json", action="store_true")

    requests = production_sub.add_parser("requests", help="Listar solicitudes")
    requests.add_argument("--creator-id", required=True)
    requests.add_argument("--json", action="store_true")

    request_create = production_sub.add_parser("request-create", help="Crear solicitud")
    request_create.add_argument("--creator-id", required=True)
    request_create.add_argument("--brief-id", required=True)
    request_create.add_argument("--request-type")
    request_create.add_argument("--json", action="store_true")

    request_show = production_sub.add_parser("request-show", help="Mostrar solicitud")
    request_show.add_argument("--request-id", required=True)
    request_show.add_argument("--json", action="store_true")

    generate = production_sub.add_parser("generate", help="Generar outline")
    generate.add_argument("--request-id")
    generate.add_argument("--creator-id")
    generate.add_argument("--brief-id")
    generate.add_argument("--request-type")
    generate.add_argument("--json", action="store_true")

    runs = production_sub.add_parser("runs", help="Corridas de produccion")
    runs.add_argument("--creator-id", required=True)
    runs.add_argument("--json", action="store_true")

    run_show = production_sub.add_parser("run-show", help="Mostrar corrida")
    run_show.add_argument("--run-id", required=True)
    run_show.add_argument("--json", action="store_true")

    run_cancel = production_sub.add_parser("run-cancel", help="Cancelar corrida")
    run_cancel.add_argument("--run-id", required=True)
    run_cancel.add_argument("--json", action="store_true")

    run_resume = production_sub.add_parser("run-resume", help="Reanudar corrida")
    run_resume.add_argument("--run-id", required=True)
    run_resume.add_argument("--json", action="store_true")

    outlines = production_sub.add_parser("outlines", help="Listar outlines")
    outlines.add_argument("--creator-id", required=True)
    outlines.add_argument("--json", action="store_true")

    outline_show = production_sub.add_parser("outline-show", help="Mostrar outline")
    outline_show.add_argument("--outline-id", required=True)
    outline_show.add_argument("--json", action="store_true")

    context = production_sub.add_parser("context", help="Contexto del outline")
    context.add_argument("--outline-id", required=True)
    context.add_argument("--json", action="store_true")

    for action in ("sections", "beats", "segments", "claims", "proofs", "scenes", "shots", "shot-groups", "recording-blocks", "recording-order", "visual-cues", "audio-cues", "on-screen-text", "broll", "graphics", "screen-recordings", "participants", "locations", "props", "wardrobe", "equipment", "continuity", "variants", "reusable-segments", "dependencies", "milestones", "checklists", "gates", "readiness", "risks"):
        sub = production_sub.add_parser(action, help=action.replace("-", " "))
        sub.add_argument("--outline-id", required=True)
        sub.add_argument("--json", action="store_true")

    reviews = production_sub.add_parser("reviews", help="Listar revisiones")
    reviews.add_argument("--outline-id", required=True)
    reviews.add_argument("--json", action="store_true")

    review = production_sub.add_parser("review", help="Revisar outline")
    review.add_argument("--outline-id", required=True)
    review.add_argument("--decision", required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--reviewer")
    review.add_argument("--json", action="store_true")

    version_create = production_sub.add_parser("version-create", help="Crear version")
    version_create.add_argument("--outline-id", required=True)
    version_create.add_argument("--reason", default="versioned_outline")
    version_create.add_argument("--json", action="store_true")

    supersede = production_sub.add_parser("supersede", help="Superseder outline")
    supersede.add_argument("--outline-id", required=True)
    supersede.add_argument("--replacement-id")
    supersede.add_argument("--reason", required=True)
    supersede.add_argument("--json", action="store_true")

    snapshot_create = production_sub.add_parser("snapshot-create", help="Crear snapshot")
    snapshot_create.add_argument("--outline-id", required=True)
    snapshot_create.add_argument("--snapshot-type", default="draft_outline")
    snapshot_create.add_argument("--json", action="store_true")

    snapshots = production_sub.add_parser("snapshots", help="Listar snapshots")
    snapshots.add_argument("--outline-id", required=True)
    snapshots.add_argument("--json", action="store_true")

    snapshot_compare = production_sub.add_parser("snapshot-compare", help="Comparar snapshots")
    snapshot_compare.add_argument("--left-id", required=True)
    snapshot_compare.add_argument("--right-id", required=True)
    snapshot_compare.add_argument("--json", action="store_true")

    report = production_sub.add_parser("report", help="Generar reporte")
    report.add_argument("--outline-id")
    report.add_argument("--creator-id", required=True)
    report.add_argument("--type", required=True, dest="report_type")
    report.add_argument("--json", action="store_true")

    export_report = production_sub.add_parser("export-report", help="Exportar reporte")
    export_report.add_argument("--report-id", required=True)
    export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export_report.add_argument("--json", action="store_true")


def handle_production_command(args, *, service: ProductionPreparationService, stdout, stderr) -> int:
    if args.action == "overview":
        print(_dump(service.build_overview(args.creator_id)), file=stdout)
        return 0
    if args.action == "requests":
        print(_dump([item.to_dict() for item in service.list_requests(args.creator_id)]), file=stdout)
        return 0
    if args.action == "request-create":
        command = CreateProductionRequestCommand(args.creator_id, args.brief_id, args.request_type)
        payload = service.create_request(creator_id=command.creator_id, content_brief_id=command.brief_id, request_type=command.request_type)
        print(_dump(payload.to_dict()), file=stdout)
        return 0
    if args.action == "request-show":
        request = service.get_request(args.request_id)
        if request is None:
            raise ProductionPreparationNotFoundError("La solicitud no existe.")
        print(_dump(request.to_dict()), file=stdout)
        return 0
    if args.action == "generate":
        command = GenerateOutlineCommand(args.request_id, args.creator_id, args.brief_id)
        payload = service.generate_outline(request_id=command.request_id, creator_id=command.creator_id, brief_id=command.brief_id, request_type=args.request_type)
        print(_dump(payload.to_dict()), file=stdout)
        return 0
    if args.action == "runs":
        print(_dump([item.to_dict() for item in service.list_tasks(args.creator_id)]), file=stdout)
        return 0
    if args.action == "run-show":
        outline = service.get_outline(args.run_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("La corrida no existe.")
        print(_dump(outline.to_dict()), file=stdout)
        return 0
    if args.action == "run-cancel":
        print(_dump(service.cancel_run(args.run_id).to_dict()), file=stdout)
        return 0
    if args.action == "run-resume":
        print(_dump(service.resume_run(args.run_id).to_dict()), file=stdout)
        return 0
    if args.action == "outlines":
        print(_dump([item.to_dict() for item in service.list_outlines(args.creator_id)]), file=stdout)
        return 0
    if args.action == "outline-show":
        outline = service.get_outline(args.outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        print(_dump(outline.to_dict()), file=stdout)
        return 0
    if args.action == "context":
        outline = service.get_outline(args.outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        context = service.get_context_snapshot(outline.production_context_snapshot_id)
        print(_dump(None if context is None else context.to_dict()), file=stdout)
        return 0
    if args.action == "sections":
        print(_dump([item.to_dict() for item in service.list_sections(args.outline_id)]), file=stdout)
        return 0
    if args.action == "beats":
        print(_dump([item.to_dict() for item in service.list_beats(args.outline_id)]), file=stdout)
        return 0
    if args.action == "segments":
        print(_dump([item.to_dict() for item in service.list_segments(args.outline_id)]), file=stdout)
        return 0
    if args.action == "claims":
        print(_dump([item.to_dict() for item in service.list_claim_links(args.outline_id)]), file=stdout)
        return 0
    if args.action == "proofs":
        print(_dump([item.to_dict() for item in service.list_proof_requirements(args.outline_id)]), file=stdout)
        return 0
    if args.action == "scenes":
        print(_dump([item.to_dict() for item in service.list_scenes(args.outline_id)]), file=stdout)
        return 0
    if args.action == "shots":
        print(_dump([item.to_dict() for item in service.list_shots(args.outline_id)]), file=stdout)
        return 0
    if args.action == "shot-groups":
        print(_dump([item.to_dict() for item in service.list_shot_groups(args.outline_id)]), file=stdout)
        return 0
    if args.action == "recording-blocks":
        print(_dump([item.to_dict() for item in service.list_recording_blocks(args.outline_id)]), file=stdout)
        return 0
    if args.action == "recording-order":
        print(_dump([item.to_dict() for item in service.list_recording_block_items(args.outline_id)]), file=stdout)
        return 0
    if args.action == "visual-cues":
        print(_dump([item.to_dict() for item in service.list_visual_cues(args.outline_id)]), file=stdout)
        return 0
    if args.action == "audio-cues":
        print(_dump([item.to_dict() for item in service.list_audio_cues(args.outline_id)]), file=stdout)
        return 0
    if args.action == "on-screen-text":
        print(_dump([item.to_dict() for item in service.list_on_screen_text(args.outline_id)]), file=stdout)
        return 0
    if args.action == "broll":
        print(_dump([item.to_dict() for item in service.list_broll_requirements(args.outline_id)]), file=stdout)
        return 0
    if args.action == "graphics":
        print(_dump([item.to_dict() for item in service.list_graphic_requirements(args.outline_id)]), file=stdout)
        return 0
    if args.action == "screen-recordings":
        print(_dump([item.to_dict() for item in service.list_screen_recordings(args.outline_id)]), file=stdout)
        return 0
    if args.action == "participants":
        print(_dump([item.to_dict() for item in service.list_participants(args.outline_id)]), file=stdout)
        return 0
    if args.action == "locations":
        print(_dump([item.to_dict() for item in service.list_locations(args.outline_id)]), file=stdout)
        return 0
    if args.action == "props":
        print(_dump([item.to_dict() for item in service.list_props(args.outline_id)]), file=stdout)
        return 0
    if args.action == "wardrobe":
        print(_dump([item.to_dict() for item in service.list_wardrobe(args.outline_id)]), file=stdout)
        return 0
    if args.action == "equipment":
        print(_dump([item.to_dict() for item in service.list_equipment(args.outline_id)]), file=stdout)
        return 0
    if args.action == "continuity":
        print(_dump([item.to_dict() for item in service.list_continuity(args.outline_id)]), file=stdout)
        return 0
    if args.action == "variants":
        print(_dump([item.to_dict() for item in service.list_variants(args.outline_id)]), file=stdout)
        return 0
    if args.action == "reusable-segments":
        print(_dump([item.to_dict() for item in service.list_reusable_segments(args.outline_id)]), file=stdout)
        return 0
    if args.action == "dependencies":
        print(_dump([item.to_dict() for item in service.list_dependencies(args.outline_id)]), file=stdout)
        return 0
    if args.action == "milestones":
        print(_dump([item.to_dict() for item in service.list_milestones(args.outline_id)]), file=stdout)
        return 0
    if args.action == "checklists":
        print(_dump([item.to_dict() for item in service.list_checklists(args.outline_id)]), file=stdout)
        return 0
    if args.action == "gates":
        print(_dump([item.to_dict() for item in service.list_gates(args.outline_id)]), file=stdout)
        return 0
    if args.action == "readiness":
        print(_dump(service.calculate_readiness(args.outline_id)), file=stdout)
        return 0
    if args.action == "risks":
        print(_dump([item.to_dict() for item in service.list_risks(args.outline_id)]), file=stdout)
        return 0
    if args.action == "reviews":
        print(_dump([item.to_dict() for item in service.list_reviews(args.outline_id)]), file=stdout)
        return 0
    if args.action == "review":
        command = ReviewOutlineCommand(args.outline_id, args.decision, args.reason)
        payload = service.review_outline(command.outline_id, decision=command.decision, reason=command.reason, reviewer=args.reviewer)
        print(_dump(payload.to_dict()), file=stdout)
        return 0
    if args.action == "version-create":
        command = VersionOutlineCommand(args.outline_id, args.reason)
        print(_dump(service.version_outline(command.outline_id, reason=command.reason).to_dict()), file=stdout)
        return 0
    if args.action == "supersede":
        print(_dump(service.supersede_outline(args.outline_id, replacement_id=args.replacement_id, reason=args.reason).to_dict()), file=stdout)
        return 0
    if args.action == "snapshot-create":
        print(_dump(service.create_snapshot(args.outline_id, snapshot_type=args.snapshot_type).to_dict()), file=stdout)
        return 0
    if args.action == "snapshots":
        print(_dump([item.to_dict() for item in service.list_snapshots(args.outline_id)]), file=stdout)
        return 0
    if args.action == "snapshot-compare":
        print(_dump(service.compare_snapshots(args.left_id, args.right_id)), file=stdout)
        return 0
    if args.action == "report":
        print(_dump(service.build_report(creator_id=args.creator_id, outline_id=args.outline_id, report_type=args.report_type).to_dict()), file=stdout)
        return 0
    if args.action == "export-report":
        print(_dump({"path": str(service.export_report(args.report_id, args.format))}), file=stdout)
        return 0
    raise ProductionPreparationNotFoundError("Accion de production desconocida.")
