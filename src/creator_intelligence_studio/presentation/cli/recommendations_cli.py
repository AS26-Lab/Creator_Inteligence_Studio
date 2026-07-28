"""CLI para Opportunity and Recommendation Engine Foundation."""

from __future__ import annotations

import json
from typing import Any

from creator_intelligence_studio.application.commands.recommendation_commands import (
    AddRecommendationOutcomeCommand,
    ConvertRecommendationToExperimentCommand,
    CreateRecommendationRequestCommand,
    GenerateRecommendationsCommand,
    ListRecommendationRequestsCommand,
    ListRecommendationsCommand,
    MarkRecommendationExecutedCommand,
    RecordRecommendationFeedbackCommand,
    ReviewRecommendationCommand,
    ShowRecommendationCommand,
    ShowRecommendationRequestCommand,
    ShowRecommendationRunCommand,
)
from creator_intelligence_studio.application.services.recommendation_engine_service import RecommendationEngineService


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


def build_recommendations_parser(subparsers) -> None:
    parser = subparsers.add_parser("recommendations", help="Opportunity and Recommendation Engine")
    recommendations_sub = parser.add_subparsers(dest="action", required=True)

    request_create = recommendations_sub.add_parser("request-create", help="Crear solicitud")
    request_create.add_argument("--creator-id", required=True)
    request_create.add_argument("--request-type", required=True)
    request_create.add_argument("--objective")
    request_create.add_argument("--platform", action="append")
    request_create.add_argument("--content-type", action="append")
    request_create.add_argument("--market-id")
    request_create.add_argument("--topic-id")
    request_create.add_argument("--time-horizon")
    request_create.add_argument("--constraints-json", default="[]")
    request_create.add_argument("--preferences-json", default="{}")
    request_create.add_argument("--json", action="store_true")

    requests = recommendations_sub.add_parser("requests", help="Listar solicitudes")
    requests.add_argument("--creator-id", required=True)
    requests.add_argument("--json", action="store_true")

    request_show = recommendations_sub.add_parser("request-show", help="Mostrar solicitud")
    request_show.add_argument("--request-id", required=True)
    request_show.add_argument("--json", action="store_true")

    generate = recommendations_sub.add_parser("generate", help="Generar recomendaciones")
    generate.add_argument("--request-id")
    generate.add_argument("--creator-id")
    generate.add_argument("--request-type")
    generate.add_argument("--objective")
    generate.add_argument("--platform", action="append")
    generate.add_argument("--content-type", action="append")
    generate.add_argument("--market-id")
    generate.add_argument("--topic-id")
    generate.add_argument("--time-horizon")
    generate.add_argument("--constraints-json", default="[]")
    generate.add_argument("--preferences-json", default="{}")
    generate.add_argument("--json", action="store_true")

    run_show = recommendations_sub.add_parser("run-show", help="Mostrar corrida")
    run_show.add_argument("--run-id", required=True)
    run_show.add_argument("--json", action="store_true")

    run_history = recommendations_sub.add_parser("run-history", help="Historial de corridas")
    run_history.add_argument("--creator-id", required=True)
    run_history.add_argument("--json", action="store_true")

    run_cancel = recommendations_sub.add_parser("run-cancel", help="Cancelar corrida")
    run_cancel.add_argument("--run-id", required=True)
    run_cancel.add_argument("--json", action="store_true")

    run_resume = recommendations_sub.add_parser("run-resume", help="Reanudar corrida")
    run_resume.add_argument("--run-id", required=True)
    run_resume.add_argument("--json", action="store_true")

    list_parser = recommendations_sub.add_parser("list", help="Listar recomendaciones")
    list_parser.add_argument("--creator-id", required=True)
    list_parser.add_argument("--status")
    list_parser.add_argument("--priority")
    list_parser.add_argument("--platform")
    list_parser.add_argument("--objective")
    list_parser.add_argument("--json", action="store_true")

    show = recommendations_sub.add_parser("show", help="Mostrar recomendacion")
    show.add_argument("--recommendation-id", required=True)
    show.add_argument("--json", action="store_true")

    evidence = recommendations_sub.add_parser("evidence", help="Evidencia de una recomendacion")
    evidence.add_argument("--recommendation-id", required=True)
    evidence.add_argument("--json", action="store_true")

    risks = recommendations_sub.add_parser("risks", help="Riesgos de una recomendacion")
    risks.add_argument("--recommendation-id", required=True)
    risks.add_argument("--json", action="store_true")

    contradictions = recommendations_sub.add_parser("contradictions", help="Contradicciones de una recomendacion")
    contradictions.add_argument("--recommendation-id", required=True)
    contradictions.add_argument("--json", action="store_true")

    alternatives = recommendations_sub.add_parser("alternatives", help="Alternativas")
    alternatives.add_argument("--recommendation-id", required=True)
    alternatives.add_argument("--json", action="store_true")

    metrics = recommendations_sub.add_parser("metrics", help="Metricas de una recomendacion")
    metrics.add_argument("--recommendation-id", required=True)
    metrics.add_argument("--json", action="store_true")

    review = recommendations_sub.add_parser("review", help="Revisar recomendacion")
    review.add_argument("--recommendation-id", required=True)
    review.add_argument("--decision", required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--reviewer")
    review.add_argument("--json", action="store_true")

    feedback = recommendations_sub.add_parser("feedback", help="Agregar feedback")
    feedback.add_argument("--recommendation-id", required=True)
    feedback.add_argument("--type", required=True, dest="feedback_type")
    feedback.add_argument("--rating", type=int)
    feedback.add_argument("--feedback-text")
    feedback.add_argument("--reason-code")
    feedback.add_argument("--json", action="store_true")

    convert = recommendations_sub.add_parser("convert-to-experiment", help="Convertir a experimento")
    convert.add_argument("--recommendation-id", required=True)
    convert.add_argument("--json", action="store_true")

    mark_executed = recommendations_sub.add_parser("mark-executed", help="Marcar como ejecutada")
    mark_executed.add_argument("--recommendation-id", required=True)
    mark_executed.add_argument("--content-id", required=True)
    mark_executed.add_argument("--json", action="store_true")

    outcome_add = recommendations_sub.add_parser("outcome-add", help="Registrar resultado")
    outcome_add.add_argument("--recommendation-id", required=True)
    outcome_add.add_argument("--file", required=True, dest="file_path")
    outcome_add.add_argument("--json", action="store_true")

    snapshots = recommendations_sub.add_parser("snapshots", help="Snapshots de recomendacion")
    snapshots.add_argument("--recommendation-id", required=True)
    snapshots.add_argument("--json", action="store_true")

    report = recommendations_sub.add_parser("report", help="Generar reporte")
    report.add_argument("--creator-id", required=True)
    report.add_argument("--type", required=True, dest="report_type")
    report.add_argument("--json", action="store_true")

    export_report = recommendations_sub.add_parser("export-report", help="Exportar reporte")
    export_report.add_argument("--report-id", required=True)
    export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export_report.add_argument("--json", action="store_true")


def _dump(payload: Any, *, json_mode: bool) -> str:
    if json_mode:
        return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)
    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)


def handle_recommendations_command(args, *, service: RecommendationEngineService, stdout, stderr) -> int:
    if args.action == "request-create":
        command = CreateRecommendationRequestCommand(
            args.creator_id,
            args.request_type,
            args.objective,
            json.dumps(args.platform or [], ensure_ascii=False),
            json.dumps(args.content_type or [], ensure_ascii=False),
            args.market_id,
            args.topic_id,
            args.time_horizon,
            args.constraints_json,
            args.preferences_json,
        )
        payload = service.create_request(
            creator_id=command.creator_id,
            request_type=command.request_type,
            objective_type=command.objective_type,
            platform_scope_json=command.platform_scope_json,
            content_type_scope_json=command.content_type_scope_json,
            market_id=command.market_id,
            topic_id=command.topic_id,
            time_horizon=command.time_horizon,
            constraints_json=command.constraints_json,
            preferences_json=command.preferences_json,
        )
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "requests":
        command = ListRecommendationRequestsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_requests(command.creator_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "request-show":
        command = ShowRecommendationRequestCommand(args.request_id)
        payload = service.get_request(command.request_id)
        if payload is None:
            print("Solicitud no encontrada.", file=stderr)
            return 1
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "generate":
        command = GenerateRecommendationsCommand(
            args.request_id,
            args.creator_id,
            args.request_type,
            args.objective,
        )
        result = service.generate_recommendations(
            request_id=command.request_id,
            creator_id=command.creator_id,
            request_type=command.request_type,
            objective_type=command.objective_type,
            platform_scope_json=json.dumps(args.platform or [], ensure_ascii=False),
            content_type_scope_json=json.dumps(args.content_type or [], ensure_ascii=False),
            market_id=args.market_id,
            topic_id=args.topic_id,
            time_horizon=args.time_horizon,
            constraints_json=args.constraints_json,
            preferences_json=args.preferences_json,
        )
        print(_dump(result.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "run-show":
        command = ShowRecommendationRunCommand(args.run_id)
        payload = service.get_run(command.run_id)
        if payload is None:
            print("Corrida no encontrada.", file=stderr)
            return 1
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "run-history":
        payload = [item.to_dict() for item in service.list_runs(args.creator_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "run-cancel":
        payload = service.cancel_run(args.run_id)
        if payload is None:
            print("Corrida no encontrada.", file=stderr)
            return 1
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "run-resume":
        payload = service.resume_run(args.run_id)
        if payload is None:
            print("Corrida no encontrada.", file=stderr)
            return 1
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "list":
        payload = [item.to_dict() for item in service.list_recommendations(args.creator_id)]
        if args.status:
            payload = [item for item in payload if item.get("status") == args.status]
        if args.priority:
            payload = [item for item in payload if item.get("priority_level") == args.priority]
        if args.platform:
            payload = [item for item in payload if args.platform in json.loads(item.get("platform_scope_json") or "[]")]
        if args.objective:
            payload = [item for item in payload if item.get("objective_type") == args.objective]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "show":
        command = ShowRecommendationCommand(args.recommendation_id)
        payload = service.get_recommendation(command.recommendation_id)
        if payload is None:
            print("Recomendacion no encontrada.", file=stderr)
            return 1
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "evidence":
        payload = [item.to_dict() for item in service.list_evidence(args.recommendation_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "risks":
        payload = [item.to_dict() for item in service.list_risks(args.recommendation_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "contradictions":
        payload = [item.to_dict() for item in service.list_contradictions(args.recommendation_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "alternatives":
        payload = [item.to_dict() for item in service.list_alternatives(args.recommendation_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "metrics":
        payload = [item.to_dict() for item in service.list_metrics(args.recommendation_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "review":
        command = ReviewRecommendationCommand(args.recommendation_id, args.decision, args.reason, reviewer=args.reviewer)
        payload = service.review_recommendation(command.recommendation_id, decision=command.decision, reason=command.reason, reviewer=command.reviewer)
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "feedback":
        command = RecordRecommendationFeedbackCommand(args.recommendation_id, args.feedback_type, rating=args.rating, feedback_text=args.feedback_text, reason_code=args.reason_code)
        payload = service.add_feedback(
            command.recommendation_id,
            feedback_type=command.feedback_type,
            rating=command.rating,
            feedback_text=command.feedback_text,
            reason_code=command.reason_code,
        )
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "convert-to-experiment":
        command = ConvertRecommendationToExperimentCommand(args.recommendation_id)
        payload = service.convert_to_experiment(command.recommendation_id)
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "mark-executed":
        command = MarkRecommendationExecutedCommand(args.recommendation_id, args.content_id)
        payload = service.mark_executed(command.recommendation_id, command.content_id)
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "outcome-add":
        command = AddRecommendationOutcomeCommand(args.recommendation_id, args.file_path)
        payload = service.add_outcome(command.recommendation_id, command.file_path)
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "snapshots":
        payload = [item.to_dict() for item in service.list_snapshots(args.recommendation_id)]
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    if args.action == "report":
        payload = service.build_report(args.creator_id, args.report_type)
        print(_dump(payload.to_dict(), json_mode=args.json), file=stdout)
        return 0
    if args.action == "export-report":
        payload = {
            "report_id": args.report_id,
            "format": args.format,
            "path": str(service.export_report(args.report_id, args.format)),
        }
        print(_dump(payload, json_mode=args.json), file=stdout)
        return 0
    raise ValueError("Accion de recommendations no reconocida.")
