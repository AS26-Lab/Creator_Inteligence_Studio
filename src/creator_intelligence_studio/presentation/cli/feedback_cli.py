"""CLI tecnica para validacion de feedback y learning signals."""

from __future__ import annotations

import argparse
import json
from typing import Any

from creator_intelligence_studio.application.services.creator_feedback_service import CreatorFeedbackService
from creator_intelligence_studio.domain.errors import DomainError


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


def _metadata(payload: str | None) -> dict[str, Any]:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _canonical_text(entity: Any) -> str:
    if entity is None:
        return ""
    if hasattr(entity, "to_dict"):
        payload = entity.to_dict()
    elif isinstance(entity, dict):
        payload = entity
    else:
        payload = {"value": str(entity)}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def build_feedback_parser(subparsers) -> None:
    parser = subparsers.add_parser("feedback", help="Superficie tecnica de feedback")
    feedback_sub = parser.add_subparsers(dest="action", required=True)

    record_edit = feedback_sub.add_parser("record-edit", help="Registrar un evento de edicion")
    record_edit.add_argument("--creator-id", required=True)
    record_edit.add_argument("--workflow-type", required=True)
    record_edit.add_argument("--artifact-type", required=True)
    record_edit.add_argument("--artifact-id", required=True)
    record_edit.add_argument("--source-version-id", required=True)
    record_edit.add_argument("--result-version-id", required=True)
    record_edit.add_argument("--project-id")
    record_edit.add_argument("--ai-execution-id")
    record_edit.add_argument("--source-text")
    record_edit.add_argument("--result-text")
    record_edit.add_argument("--dedupe-key")
    record_edit.add_argument("--json", action="store_true")


def handle_feedback_command(
    args: argparse.Namespace,
    *,
    service: CreatorFeedbackService,
    stdout,
    stderr,
    catalog_service: Any | None = None,
    planning_service: Any | None = None,
    brief_service: Any | None = None,
    production_service: Any | None = None,
) -> int:
    try:
        if args.action == "record-edit":
            supported_artifacts = {"content_brief", "script_outline", "strategic_plan"}
            if args.artifact_type not in supported_artifacts:
                raise DomainError("El comando record-edit solo soporta content_brief, script_outline y strategic_plan.")
            if args.project_id and catalog_service is not None:
                project = catalog_service.get_project(args.project_id)
                if project.creator_id != args.creator_id:
                    raise DomainError("El proyecto no pertenece al creador indicado.")
            source_text = args.source_text
            result_text = args.result_text
            if source_text is None or result_text is None:
                if args.artifact_type == "content_brief" and brief_service is not None:
                    source = brief_service.get_brief(args.source_version_id)
                    result = brief_service.get_brief(args.result_version_id)
                    source_text = source_text if source_text is not None else _canonical_text(source)
                    result_text = result_text if result_text is not None else _canonical_text(result)
                elif args.artifact_type == "script_outline" and production_service is not None:
                    source = production_service.get_outline(args.source_version_id)
                    result = production_service.get_outline(args.result_version_id)
                    source_text = source_text if source_text is not None else _canonical_text(source)
                    result_text = result_text if result_text is not None else _canonical_text(result)
                elif args.artifact_type == "strategic_plan" and planning_service is not None:
                    source = planning_service.get_plan(args.source_version_id)
                    result = planning_service.get_plan(args.result_version_id)
                    source_text = source_text if source_text is not None else _canonical_text(source)
                    result_text = result_text if result_text is not None else _canonical_text(result)
                elif source_text is None or result_text is None:
                    raise DomainError("El comando record-edit requiere source_text y result_text cuando no puede resolver versiones canonicas.")
            metadata = {
                "source_text": source_text,
                "result_text": result_text,
            }
            payload = service.record_edit(
                creator_id=args.creator_id,
                project_id=args.project_id,
                workflow_type=args.workflow_type,
                artifact_type=args.artifact_type,
                artifact_id=args.artifact_id,
                source_version_id=args.source_version_id,
                result_version_id=args.result_version_id,
                ai_execution_id=args.ai_execution_id,
                metadata=metadata,
                dedupe_key=args.dedupe_key,
            )
            diff_summary = _metadata(payload.metadata_json).get("diff_summary", {})
            summary = {
                "id": payload.id,
                "event_type": payload.event_type.value,
                "creator_id": payload.creator_id,
                "project_id": payload.project_id,
                "workflow_type": payload.workflow_type,
                "artifact_type": payload.artifact_type,
                "artifact_id": payload.artifact_id,
                "source_version_id": payload.source_version_id,
                "result_version_id": payload.result_version_id,
                "diff_algorithm_version": diff_summary.get("algorithm_version"),
                "words_before": diff_summary.get("before_words"),
                "words_after": diff_summary.get("after_words"),
                "words_added": diff_summary.get("insertions"),
                "words_removed": diff_summary.get("deletions"),
                "change_ratio": diff_summary.get("changed_ratio"),
            }
            print(_dump(summary), file=stdout)
            return 0
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
    raise ValueError("Accion de feedback no reconocida.")
