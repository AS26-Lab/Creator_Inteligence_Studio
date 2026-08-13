"""CLI para Strategic Planning and Content Roadmap Foundation."""

from __future__ import annotations

import json
from typing import Any

from creator_intelligence_studio.application.commands.strategic_planning_commands import (
    CreatePlanningContextCommand,
    CreateRoadmapItemCommand,
    CreateStrategicObjectiveCommand,
    CreateStrategicPlanCommand,
    IntakeRecommendationCommand,
    ReviewStrategicPlanCommand,
)
from creator_intelligence_studio.application.services.strategic_planning_service import StrategicPlanningService
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.domain.strategic_planning.errors import StrategicPlanningNotFoundError
from creator_intelligence_studio.domain.strategic_planning.entities import ContentPillar, Initiative, PlanningConflict, PlanningScenario, PlanningSnapshot, StrategicObjective, StrategyTheme


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


def build_planning_parser(subparsers) -> None:
    parser = subparsers.add_parser("planning", help="Strategic Planning")
    planning_sub = parser.add_subparsers(dest="action", required=True)

    overview = planning_sub.add_parser("overview", help="Resumen estrategico")
    overview.add_argument("--creator-id", required=True)
    overview.add_argument("--json", action="store_true")

    plans = planning_sub.add_parser("plans", help="Listar planes")
    plans.add_argument("--creator-id", required=True)
    plans.add_argument("--json", action="store_true")

    plan_create = planning_sub.add_parser("plan-create", help="Crear plan estrategico")
    plan_create.add_argument("--creator-id", required=True)
    plan_create.add_argument("--name", required=True)
    plan_create.add_argument("--horizon", required=True)
    plan_create.add_argument("--context-snapshot-id", required=True)
    plan_create.add_argument("--description")
    plan_create.add_argument("--start-date")
    plan_create.add_argument("--end-date")
    plan_create.add_argument("--timezone")
    plan_create.add_argument("--json", action="store_true")

    plan_show = planning_sub.add_parser("plan-show", help="Mostrar plan")
    plan_show.add_argument("--plan-id", required=True)
    plan_show.add_argument("--json", action="store_true")

    context_snapshot_create = planning_sub.add_parser("context-snapshot-create", help="Crear snapshot de contexto estrategico")
    context_snapshot_create.add_argument("--creator-id", required=True)
    context_snapshot_create.add_argument("--project-id")
    context_snapshot_create.add_argument("--recommendation-snapshot-id")
    context_snapshot_create.add_argument("--json", action="store_true")

    plan_update = planning_sub.add_parser("plan-update", help="Actualizar plan")
    plan_update.add_argument("--plan-id", required=True)
    plan_update.add_argument("--name")
    plan_update.add_argument("--status")
    plan_update.add_argument("--json", action="store_true")

    plan_review = planning_sub.add_parser("plan-review", help="Revisar plan")
    plan_review.add_argument("--plan-id", required=True)
    plan_review.add_argument("--decision", required=True)
    plan_review.add_argument("--reason", required=True)
    plan_review.add_argument("--reviewer")
    plan_review.add_argument("--json", action="store_true")

    for action_name in ("plan-activate", "plan-pause", "plan-archive", "plan-version-create"):
        sub = planning_sub.add_parser(action_name, help=action_name.replace("-", " "))
        sub.add_argument("--plan-id", required=True)
        sub.add_argument("--json", action="store_true")
        if action_name == "plan-archive":
            sub.add_argument("--reason", default="archive")
        elif action_name == "plan-pause":
            sub.add_argument("--reason", default="pause")
        elif action_name == "plan-activate":
            sub.add_argument("--reason", default="manual_activation")
        elif action_name == "plan-version-create":
            sub.add_argument("--name")
            sub.add_argument("--reason", default="versioned_plan")

    objectives = planning_sub.add_parser("objectives", help="Listar objetivos")
    objectives.add_argument("--plan-id", required=True)
    objectives.add_argument("--json", action="store_true")

    objective_create = planning_sub.add_parser("objective-create", help="Crear objetivo")
    objective_create.add_argument("--plan-id", required=True)
    objective_create.add_argument("--type", required=True, dest="objective_type")
    objective_create.add_argument("--title", required=True)
    objective_create.add_argument("--priority", default="medium")
    objective_create.add_argument("--status", default="draft")
    objective_create.add_argument("--json", action="store_true")

    objective_show = planning_sub.add_parser("objective-show", help="Mostrar objetivo")
    objective_show.add_argument("--objective-id", required=True)
    objective_show.add_argument("--json", action="store_true")

    objective_update = planning_sub.add_parser("objective-update", help="Actualizar objetivo")
    objective_update.add_argument("--objective-id", required=True)
    objective_update.add_argument("--title")
    objective_update.add_argument("--status")
    objective_update.add_argument("--json", action="store_true")

    objective_review = planning_sub.add_parser("objective-review", help="Revisar objetivo")
    objective_review.add_argument("--objective-id", required=True)
    objective_review.add_argument("--decision", required=True)
    objective_review.add_argument("--reason", required=True)
    objective_review.add_argument("--json", action="store_true")

    themes = planning_sub.add_parser("themes", help="Listar themes")
    themes.add_argument("--plan-id", required=True)
    themes.add_argument("--json", action="store_true")

    theme_create = planning_sub.add_parser("theme-create", help="Crear theme")
    theme_create.add_argument("--plan-id", required=True)
    theme_create.add_argument("--name", required=True)
    theme_create.add_argument("--type", default="unknown", dest="theme_type")
    theme_create.add_argument("--json", action="store_true")

    theme_show = planning_sub.add_parser("theme-show", help="Mostrar theme")
    theme_show.add_argument("--theme-id", required=True)
    theme_show.add_argument("--json", action="store_true")

    pillars = planning_sub.add_parser("pillars", help="Listar pilares")
    pillars.add_argument("--plan-id", required=True)
    pillars.add_argument("--json", action="store_true")

    pillar_create = planning_sub.add_parser("pillar-create", help="Crear pilar")
    pillar_create.add_argument("--plan-id", required=True)
    pillar_create.add_argument("--name", required=True)
    pillar_create.add_argument("--theme-id")
    pillar_create.add_argument("--json", action="store_true")

    pillar_show = planning_sub.add_parser("pillar-show", help="Mostrar pilar")
    pillar_show.add_argument("--pillar-id", required=True)
    pillar_show.add_argument("--json", action="store_true")

    pillar_update = planning_sub.add_parser("pillar-update", help="Actualizar pilar")
    pillar_update.add_argument("--pillar-id", required=True)
    pillar_update.add_argument("--name")
    pillar_update.add_argument("--status")
    pillar_update.add_argument("--json", action="store_true")

    recommendations = planning_sub.add_parser("recommendations", help="Recomendaciones hacia plan")
    recommendations.add_argument("--plan-id", required=True)
    recommendations.add_argument("--json", action="store_true")

    recommendation_intake = planning_sub.add_parser("recommendation-intake", help="Intake de recomendacion")
    recommendation_intake.add_argument("--plan-id", required=True)
    recommendation_intake.add_argument("--recommendation-id", required=True)
    recommendation_intake.add_argument("--status", default="approved", dest="intake_status")
    recommendation_intake.add_argument("--reason", default="")
    recommendation_intake.add_argument("--json", action="store_true")

    initiatives = planning_sub.add_parser("initiatives", help="Listar iniciativas")
    initiatives.add_argument("--plan-id", required=True)
    initiatives.add_argument("--json", action="store_true")

    initiative_create = planning_sub.add_parser("initiative-create", help="Crear iniciativa")
    initiative_create.add_argument("--plan-id", required=True)
    initiative_create.add_argument("--title", required=True)
    initiative_create.add_argument("--type", default="unknown", dest="initiative_type")
    initiative_create.add_argument("--objective-id")
    initiative_create.add_argument("--pillar-id")
    initiative_create.add_argument("--recommendation-id")
    initiative_create.add_argument("--experiment-id")
    initiative_create.add_argument("--json", action="store_true")

    initiative_show = planning_sub.add_parser("initiative-show", help="Mostrar iniciativa")
    initiative_show.add_argument("--initiative-id", required=True)
    initiative_show.add_argument("--json", action="store_true")

    campaigns = planning_sub.add_parser("campaigns", help="Listar campañas")
    campaigns.add_argument("--plan-id", required=True)
    campaigns.add_argument("--json", action="store_true")

    campaign_create = planning_sub.add_parser("campaign-create", help="Crear campaña")
    campaign_create.add_argument("--plan-id", required=True)
    campaign_create.add_argument("--name", required=True)
    campaign_create.add_argument("--type", default="unknown", dest="campaign_type")
    campaign_create.add_argument("--initiative-id")
    campaign_create.add_argument("--json", action="store_true")

    series = planning_sub.add_parser("series", help="Listar series")
    series.add_argument("--plan-id", required=True)
    series.add_argument("--json", action="store_true")

    series_create = planning_sub.add_parser("series-create", help="Crear serie")
    series_create.add_argument("--plan-id", required=True)
    series_create.add_argument("--name", required=True)
    series_create.add_argument("--type", default="unknown", dest="series_type")
    series_create.add_argument("--initiative-id")
    series_create.add_argument("--campaign-id")
    series_create.add_argument("--json", action="store_true")

    cycles = planning_sub.add_parser("cycles", help="Listar ciclos")
    cycles.add_argument("--plan-id", required=True)
    cycles.add_argument("--json", action="store_true")

    cycle_create = planning_sub.add_parser("cycle-create", help="Crear ciclo")
    cycle_create.add_argument("--plan-id", required=True)
    cycle_create.add_argument("--name", required=True)
    cycle_create.add_argument("--type", required=True, dest="cycle_type")
    cycle_create.add_argument("--start-date", required=True)
    cycle_create.add_argument("--end-date", required=True)
    cycle_create.add_argument("--json", action="store_true")

    roadmap = planning_sub.add_parser("roadmap", help="Listar roadmap")
    roadmap.add_argument("--plan-id", required=True)
    roadmap.add_argument("--json", action="store_true")

    roadmap_item_create = planning_sub.add_parser("roadmap-item-create", help="Crear roadmap item")
    roadmap_item_create.add_argument("--plan-id", required=True)
    roadmap_item_create.add_argument("--title", required=True)
    roadmap_item_create.add_argument("--type", required=True, dest="item_type")
    roadmap_item_create.add_argument("--initiative-id")
    roadmap_item_create.add_argument("--recommendation-id")
    roadmap_item_create.add_argument("--experiment-id")
    roadmap_item_create.add_argument("--internal-content-id")
    roadmap_item_create.add_argument("--tentative-start")
    roadmap_item_create.add_argument("--tentative-end")
    roadmap_item_create.add_argument("--confirmed-start")
    roadmap_item_create.add_argument("--confirmed-end")
    roadmap_item_create.add_argument("--json", action="store_true")

    roadmap_item_show = planning_sub.add_parser("roadmap-item-show", help="Mostrar roadmap item")
    roadmap_item_show.add_argument("--item-id", required=True)
    roadmap_item_show.add_argument("--json", action="store_true")

    roadmap_item_update = planning_sub.add_parser("roadmap-item-update", help="Actualizar roadmap item")
    roadmap_item_update.add_argument("--item-id", required=True)
    roadmap_item_update.add_argument("--title")
    roadmap_item_update.add_argument("--status")
    roadmap_item_update.add_argument("--json", action="store_true")

    roadmap_item_review = planning_sub.add_parser("roadmap-item-review", help="Revisar roadmap item")
    roadmap_item_review.add_argument("--item-id", required=True)
    roadmap_item_review.add_argument("--decision", required=True)
    roadmap_item_review.add_argument("--reason", required=True)
    roadmap_item_review.add_argument("--json", action="store_true")

    backlog = planning_sub.add_parser("backlog", help="Listar backlog")
    backlog.add_argument("--plan-id", required=True)
    backlog.add_argument("--json", action="store_true")

    backlog_add = planning_sub.add_parser("backlog-add", help="Agregar backlog")
    backlog_add.add_argument("--plan-id", required=True)
    backlog_add.add_argument("--title", required=True)
    backlog_add.add_argument("--source-type", required=True)
    backlog_add.add_argument("--source-id")
    backlog_add.add_argument("--json", action="store_true")

    capacity = planning_sub.add_parser("capacity", help="Capacidad")
    capacity.add_argument("--plan-id", required=True)
    capacity.add_argument("--json", action="store_true")

    capacity_set = planning_sub.add_parser("capacity-set", help="Configurar capacidad")
    capacity_set.add_argument("--plan-id", required=True)
    capacity_set.add_argument("--creator-id", required=True)
    capacity_set.add_argument("--name", required=True)
    capacity_set.add_argument("--available-units", type=float)
    capacity_set.add_argument("--available-hours", type=float)
    capacity_set.add_argument("--json", action="store_true")

    capacity_check = planning_sub.add_parser("capacity-check", help="Verificar capacidad")
    capacity_check.add_argument("--plan-id", required=True)
    capacity_check.add_argument("--json", action="store_true")

    dependencies = planning_sub.add_parser("dependencies", help="Listar dependencias")
    dependencies.add_argument("--plan-id", required=True)
    dependencies.add_argument("--json", action="store_true")

    dependency_add = planning_sub.add_parser("dependency-add", help="Agregar dependencia")
    dependency_add.add_argument("--item-id", required=True)
    dependency_add.add_argument("--depends-on", required=True)
    dependency_add.add_argument("--type", default="finish_to_start", dest="dependency_type")
    dependency_add.add_argument("--reason", default="manual")
    dependency_add.add_argument("--json", action="store_true")

    dependency_remove = planning_sub.add_parser("dependency-remove", help="Eliminar dependencia")
    dependency_remove.add_argument("--dependency-id", required=True)
    dependency_remove.add_argument("--json", action="store_true")

    dependency_check = planning_sub.add_parser("dependency-check", help="Verificar dependencias")
    dependency_check.add_argument("--plan-id", required=True)
    dependency_check.add_argument("--json", action="store_true")

    milestones = planning_sub.add_parser("milestones", help="Listar milestones")
    milestones.add_argument("--item-id", required=True)
    milestones.add_argument("--json", action="store_true")

    milestone_add = planning_sub.add_parser("milestone-add", help="Agregar milestone")
    milestone_add.add_argument("--item-id", required=True)
    milestone_add.add_argument("--title", required=True)
    milestone_add.add_argument("--type", default="custom", dest="milestone_type")
    milestone_add.add_argument("--json", action="store_true")

    conflicts = planning_sub.add_parser("conflicts", help="Listar conflictos")
    conflicts.add_argument("--plan-id", required=True)
    conflicts.add_argument("--json", action="store_true")

    conflict_show = planning_sub.add_parser("conflict-show", help="Mostrar conflicto")
    conflict_show.add_argument("--conflict-id", required=True)
    conflict_show.add_argument("--json", action="store_true")

    conflict_review = planning_sub.add_parser("conflict-review", help="Revisar conflicto")
    conflict_review.add_argument("--conflict-id", required=True)
    conflict_review.add_argument("--decision", required=True)
    conflict_review.add_argument("--reason", required=True)
    conflict_review.add_argument("--json", action="store_true")

    scenarios = planning_sub.add_parser("scenarios", help="Listar escenarios")
    scenarios.add_argument("--plan-id", required=True)
    scenarios.add_argument("--json", action="store_true")

    scenario_build = planning_sub.add_parser("scenario-build", help="Construir escenario")
    scenario_build.add_argument("--plan-id", required=True)
    scenario_build.add_argument("--type", required=True, dest="scenario_type")
    scenario_build.add_argument("--json", action="store_true")

    scenario_show = planning_sub.add_parser("scenario-show", help="Mostrar escenario")
    scenario_show.add_argument("--scenario-id", required=True)
    scenario_show.add_argument("--json", action="store_true")

    scenario_compare = planning_sub.add_parser("scenario-compare", help="Comparar escenarios")
    scenario_compare.add_argument("--left-id", required=True)
    scenario_compare.add_argument("--right-id", required=True)
    scenario_compare.add_argument("--json", action="store_true")

    snapshots = planning_sub.add_parser("snapshots", help="Listar snapshots")
    snapshots.add_argument("--plan-id", required=True)
    snapshots.add_argument("--json", action="store_true")

    snapshot_compare = planning_sub.add_parser("snapshot-compare", help="Comparar snapshots")
    snapshot_compare.add_argument("--left-id", required=True)
    snapshot_compare.add_argument("--right-id", required=True)
    snapshot_compare.add_argument("--json", action="store_true")

    report = planning_sub.add_parser("report", help="Crear reporte")
    report.add_argument("--plan-id")
    report.add_argument("--creator-id", required=True)
    report.add_argument("--type", required=True, dest="report_type")
    report.add_argument("--json", action="store_true")

    export_report = planning_sub.add_parser("export-report", help="Exportar reporte")
    export_report.add_argument("--report-id", required=True)
    export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export_report.add_argument("--json", action="store_true")


def handle_planning_command(args, *, service: StrategicPlanningService, stdout, stderr, catalog_service=None) -> int:
    try:
        if args.action == "overview":
            payload = service.build_overview(args.creator_id) if service.list_plans(args.creator_id) else {"creator_id": args.creator_id, "plans": []}
            print(_dump(payload), file=stdout)
            return 0
        if args.action == "plans":
            print(_dump([item.to_dict() for item in service.list_plans(args.creator_id)]), file=stdout)
            return 0
        if args.action == "plan-create":
            command = CreateStrategicPlanCommand(args.creator_id, args.name, args.horizon, args.context_snapshot_id)
            plan = service.create_plan(
                creator_id=command.creator_id,
                name=command.name,
                horizon_type=command.horizon,
                context_snapshot_id=command.context_snapshot_id,
                description=args.description,
                start_date=args.start_date,
                end_date=args.end_date,
                timezone=args.timezone,
            )
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "context-snapshot-create":
            project_id = getattr(args, "project_id", None)
            if project_id and catalog_service is not None:
                project = catalog_service.get_project(project_id)
                if project.creator_id != args.creator_id:
                    raise DomainError("El proyecto no pertenece al creador indicado.")
            command = CreatePlanningContextCommand(args.creator_id)
            snapshot = service.create_context_snapshot(
                command.creator_id,
                recommendation_snapshot_id=args.recommendation_snapshot_id,
            )
            print(
                _dump(
                    {
                        "snapshot_id": snapshot.id,
                        "creator_id": snapshot.creator_id,
                        "project_id": project_id,
                        "snapshot_type": "planning_context_snapshot",
                        "context_version": snapshot.context_version,
                    }
                ),
                file=stdout,
            )
            return 0
        if args.action == "plan-show":
            plan = service.get_plan(args.plan_id)
            if plan is None:
                print("Plan no encontrado.", file=stderr)
                return 1
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "plan-update":
            plan = service.update_plan(args.plan_id, name=args.name, status=args.status)
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "plan-review":
            command = ReviewStrategicPlanCommand(args.plan_id, args.decision, args.reason)
            review = service.record_review(strategic_plan_id=command.plan_id, target_type="plan", target_id=command.plan_id, review_type="plan_review", decision=command.decision, reason=command.reason, reviewer=args.reviewer)
            print(_dump(review.to_dict()), file=stdout)
            return 0
        if args.action == "plan-activate":
            plan = service.activate_plan(args.plan_id, reason=args.reason)
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "plan-pause":
            plan = service.pause_plan(args.plan_id, reason=args.reason)
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "plan-archive":
            plan = service.archive_plan(args.plan_id, reason=args.reason)
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "plan-version-create":
            plan = service.version_plan(args.plan_id, name=args.name, reason=args.reason)
            print(_dump(plan.to_dict()), file=stdout)
            return 0
        if args.action == "objectives":
            print(_dump([item.to_dict() for item in service.list_objectives(args.plan_id)]), file=stdout)
            return 0
        if args.action == "objective-create":
            command = CreateStrategicObjectiveCommand(args.plan_id, args.objective_type, args.title)
            objective = service.create_objective(strategic_plan_id=command.plan_id, objective_type=command.objective_type, title=command.title, priority_level=args.priority, status=args.status, source_type="manual", metrics=[])
            print(_dump(objective.to_dict()), file=stdout)
            return 0
        if args.action == "objective-show":
            objective = service.get_objective(args.objective_id)
            if objective is None:
                print("Objetivo no encontrado.", file=stderr)
                return 1
            print(_dump(objective.to_dict()), file=stdout)
            return 0
        if args.action == "objective-update":
            objective = service.update_objective(args.objective_id, title=args.title, status=args.status)
            print(_dump(objective.to_dict()), file=stdout)
            return 0
        if args.action == "objective-review":
            objective = service.get_objective(args.objective_id)
            if objective is None:
                print("Objetivo no encontrado.", file=stderr)
                return 1
            review = service.record_review(strategic_plan_id=objective.strategic_plan_id, target_type="objective", target_id=args.objective_id, review_type="objective_review", decision=args.decision, reason=args.reason)
            print(_dump(review.to_dict()), file=stdout)
            return 0
        if args.action == "themes":
            print(_dump([item.to_dict() for item in service.list_themes(args.plan_id)]), file=stdout)
            return 0
        if args.action == "theme-create":
            theme = service.create_theme(strategic_plan_id=args.plan_id, name=args.name, theme_type=args.theme_type)
            print(_dump(theme.to_dict()), file=stdout)
            return 0
        if args.action == "theme-show":
            theme = service._fetch_entity("strategy_themes", StrategyTheme, where="id = ?", params=(args.theme_id,))
            if theme is None:
                print("Theme no encontrado.", file=stderr)
                return 1
            print(_dump(theme.to_dict()), file=stdout)
            return 0
        if args.action == "pillars":
            print(_dump([item.to_dict() for item in service.list_pillars(args.plan_id)]), file=stdout)
            return 0
        if args.action == "pillar-create":
            pillar = service.create_pillar(strategic_plan_id=args.plan_id, name=args.name, strategy_theme_id=args.theme_id)
            print(_dump(pillar.to_dict()), file=stdout)
            return 0
        if args.action == "pillar-show":
            pillar = service._fetch_entity("content_pillars", ContentPillar, where="id = ?", params=(args.pillar_id,))
            if pillar is None:
                print("Pilar no encontrado.", file=stderr)
                return 1
            print(_dump(pillar.to_dict()), file=stdout)
            return 0
        if args.action == "pillar-update":
            pillar = service._fetch_entity("content_pillars", ContentPillar, where="id = ?", params=(args.pillar_id,))
            if pillar is None:
                print("Pilar no encontrado.", file=stderr)
                return 1
            updated = service._upsert("content_pillars", {**pillar.to_dict(), "name": args.name or pillar.name, "status": args.status or pillar.status.value})
            print(_dump(updated), file=stdout)
            return 0
        if args.action == "recommendations":
            recommendations = []
            if service.recommendation_service is not None:
                recommendations = [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in (service.recommendation_service.list_recommendations(args.plan_id) or [])]
            print(_dump(recommendations), file=stdout)
            return 0
        if args.action == "recommendation-intake":
            command = IntakeRecommendationCommand(args.plan_id, args.recommendation_id, args.intake_status)
            payload = service.intake_recommendation(strategic_plan_id=command.plan_id, recommendation_id=command.recommendation_id, intake_status=command.intake_status, reason=args.reason)
            print(_dump(payload), file=stdout)
            return 0
        if args.action == "initiatives":
            print(_dump([item.to_dict() for item in service.list_initiatives(args.plan_id)]), file=stdout)
            return 0
        if args.action == "initiative-create":
            initiative = service.create_initiative(strategic_plan_id=args.plan_id, title=args.title, initiative_type=args.initiative_type, strategic_objective_id=args.objective_id, content_pillar_id=args.pillar_id, recommendation_candidate_id=args.recommendation_id, experiment_id=args.experiment_id)
            print(_dump(initiative.to_dict()), file=stdout)
            return 0
        if args.action == "initiative-show":
            initiative = service._fetch_entity("strategic_initiatives", Initiative, where="id = ?", params=(args.initiative_id,))
            if initiative is None:
                print("Iniciativa no encontrada.", file=stderr)
                return 1
            print(_dump(initiative.to_dict()), file=stdout)
            return 0
        if args.action == "campaigns":
            print(_dump([item.to_dict() for item in service.list_campaigns(args.plan_id)]), file=stdout)
            return 0
        if args.action == "campaign-create":
            campaign = service.create_campaign(strategic_plan_id=args.plan_id, name=args.name, campaign_type=args.campaign_type, strategic_initiative_id=args.initiative_id)
            print(_dump(campaign.to_dict()), file=stdout)
            return 0
        if args.action == "series":
            print(_dump([item.to_dict() for item in service.list_series(args.plan_id)]), file=stdout)
            return 0
        if args.action == "series-create":
            series = service.create_series(strategic_plan_id=args.plan_id, name=args.name, series_type=args.series_type, strategic_initiative_id=args.initiative_id, campaign_id=args.campaign_id)
            print(_dump(series.to_dict()), file=stdout)
            return 0
        if args.action == "cycles":
            print(_dump([item.to_dict() for item in service.list_cycles(args.plan_id)]), file=stdout)
            return 0
        if args.action == "cycle-create":
            cycle = service.create_cycle(strategic_plan_id=args.plan_id, name=args.name, cycle_type=args.cycle_type, start_date=args.start_date, end_date=args.end_date)
            print(_dump(cycle.to_dict()), file=stdout)
            return 0
        if args.action == "roadmap":
            print(_dump([item.to_dict() for item in service.list_roadmap_items(args.plan_id)]), file=stdout)
            return 0
        if args.action == "roadmap-item-create":
            item = service.add_roadmap_item(
                strategic_plan_id=args.plan_id,
                title=args.title,
                item_type=args.item_type,
                strategic_initiative_id=args.initiative_id,
                recommendation_candidate_id=args.recommendation_id,
                experiment_id=args.experiment_id,
                internal_content_id=args.internal_content_id,
                tentative_start=args.tentative_start,
                tentative_end=args.tentative_end,
                confirmed_start=args.confirmed_start,
                confirmed_end=args.confirmed_end,
            )
            print(_dump(item.to_dict()), file=stdout)
            return 0
        if args.action == "roadmap-item-show":
            item = service.get_roadmap_item(args.item_id)
            if item is None:
                print("Roadmap item no encontrado.", file=stderr)
                return 1
            print(_dump(item.to_dict()), file=stdout)
            return 0
        if args.action == "roadmap-item-update":
            item = service.update_roadmap_item(args.item_id, title=args.title, status=args.status)
            print(_dump(item.to_dict()), file=stdout)
            return 0
        if args.action == "roadmap-item-review":
            review = service.record_review(strategic_plan_id=service.get_roadmap_item(args.item_id).strategic_plan_id if service.get_roadmap_item(args.item_id) else "", target_type="roadmap_item", target_id=args.item_id, review_type="milestone_review", decision=args.decision, reason=args.reason)
            print(_dump(review.to_dict()), file=stdout)
            return 0
        if args.action == "backlog":
            print(_dump([item.to_dict() for item in service.list_backlog_items(args.plan_id)]), file=stdout)
            return 0
        if args.action == "backlog-add":
            item = service.create_backlog_item(strategic_plan_id=args.plan_id, source_type=args.source_type, source_id=args.source_id, title=args.title)
            print(_dump(item.to_dict()), file=stdout)
            return 0
        if args.action == "capacity":
            print(_dump(service.calculate_capacity_load(args.plan_id)), file=stdout)
            return 0
        if args.action == "capacity-set":
            profile = service.create_capacity_profile(strategic_plan_id=args.plan_id, creator_id=args.creator_id, name=args.name, available_capacity_units=args.available_units, available_hours=args.available_hours)
            print(_dump(profile.to_dict()), file=stdout)
            return 0
        if args.action == "capacity-check":
            print(_dump(service.calculate_capacity_load(args.plan_id)), file=stdout)
            return 0
        if args.action == "dependencies":
            print(_dump(service.build_dependency_graph(args.plan_id)), file=stdout)
            return 0
        if args.action == "dependency-add":
            dependency = service.create_dependency(roadmap_item_id=args.item_id, depends_on_roadmap_item_id=args.depends_on, dependency_type=args.dependency_type, reason=args.reason)
            print(_dump(dependency.to_dict()), file=stdout)
            return 0
        if args.action == "dependency-remove":
            print(_dump({"deleted": service.remove_dependency(args.dependency_id)}), file=stdout)
            return 0
        if args.action == "dependency-check":
            print(_dump(service.build_dependency_graph(args.plan_id)), file=stdout)
            return 0
        if args.action == "milestones":
            print(_dump([item.to_dict() for item in service.list_milestones(args.item_id)]), file=stdout)
            return 0
        if args.action == "milestone-add":
            milestone = service.create_milestone(roadmap_item_id=args.item_id, title=args.title, milestone_type=args.milestone_type)
            print(_dump(milestone.to_dict()), file=stdout)
            return 0
        if args.action == "conflicts":
            print(_dump([item.to_dict() for item in service.list_conflicts(args.plan_id)]), file=stdout)
            return 0
        if args.action == "conflict-show":
            conflict = service._fetch_entity("planning_conflicts", PlanningConflict, where="id = ?", params=(args.conflict_id,))
            if conflict is None:
                print("Conflicto no encontrado.", file=stderr)
                return 1
            print(_dump(conflict.to_dict()), file=stdout)
            return 0
        if args.action == "conflict-review":
            conflict = service._fetch_entity("planning_conflicts", PlanningConflict, where="id = ?", params=(args.conflict_id,))
            if conflict is None:
                print("Conflicto no encontrado.", file=stderr)
                return 1
            review = service.record_review(strategic_plan_id=conflict.strategic_plan_id, target_type="conflict", target_id=args.conflict_id, review_type="risk_review", decision=args.decision, reason=args.reason)
            print(_dump(review.to_dict()), file=stdout)
            return 0
        if args.action == "scenarios":
            print(_dump([item.to_dict() for item in service.list_scenarios(args.plan_id)]), file=stdout)
            return 0
        if args.action == "scenario-build":
            scenario = service.build_scenario(args.plan_id, args.scenario_type)
            print(_dump(scenario.to_dict()), file=stdout)
            return 0
        if args.action == "scenario-show":
            scenario = service._fetch_entity("planning_scenarios", PlanningScenario, where="id = ?", params=(args.scenario_id,))
            if scenario is None:
                print("Escenario no encontrado.", file=stderr)
                return 1
            print(_dump(scenario.to_dict()), file=stdout)
            return 0
        if args.action == "scenario-compare":
            print(_dump(service.compare_scenarios(args.left_id, args.right_id)), file=stdout)
            return 0
        if args.action == "snapshots":
            print(_dump([item.to_dict() for item in service.list_snapshots(args.plan_id)]), file=stdout)
            return 0
        if args.action == "snapshot-compare":
            left = service.get_context_snapshot(args.left_id)
            right = service.get_context_snapshot(args.right_id)
            print(_dump({"left": None if left is None else left.to_dict(), "right": None if right is None else right.to_dict()}), file=stdout)
            return 0
        if args.action == "report":
            report = service.build_report(strategic_plan_id=args.plan_id, creator_id=args.creator_id, report_type=args.report_type)
            print(_dump(report.to_dict()), file=stdout)
            return 0
        if args.action == "export-report":
            path = service.export_report(args.report_id, args.format)
            print(_dump({"report_id": args.report_id, "format": args.format, "path": str(path)}), file=stdout)
            return 0
    except StrategicPlanningNotFoundError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
    raise ValueError("Accion de planning no reconocida.")
