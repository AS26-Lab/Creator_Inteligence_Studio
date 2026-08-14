"""CLI technical surface for Creator Voice evidence snapshots."""

from __future__ import annotations

import argparse
import json
from typing import Any

from creator_intelligence_studio.application.services.creator_voice_evidence_service import CreatorVoiceEvidenceService
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


def build_voice_parser(subparsers) -> None:
    parser = subparsers.add_parser("voice", help="Evidencia de Creator Voice")
    voice_sub = parser.add_subparsers(dest="action", required=True)

    snapshot = voice_sub.add_parser("evidence-snapshot", help="Construir un snapshot de evidencia de voz")
    snapshot.add_argument("--creator-id", required=True)
    snapshot.add_argument("--project-id")
    snapshot.add_argument("--workflow-type")
    snapshot.add_argument("--language")
    snapshot.add_argument("--include-historical-versions", action="store_true")
    snapshot.add_argument("--include-creator-global", action="store_true")
    snapshot.add_argument("--json", action="store_true")
    snapshot.add_argument("--debug", action="store_true")
    snapshot.add_argument("--max-items", type=int, default=24)
    snapshot.add_argument("--max-items-per-source", type=int, default=3)
    snapshot.add_argument("--max-items-per-type", type=int, default=8)


def handle_voice_command(
    args: argparse.Namespace,
    *,
    service: CreatorVoiceEvidenceService,
    stdout,
    stderr,
) -> int:
    try:
        if args.action == "evidence-snapshot":
            payload = service.diagnostics(
                {
                    "creator_id": args.creator_id,
                    "project_id": args.project_id,
                    "workflow_type": args.workflow_type,
                    "language": args.language,
                    "include_historical_versions": bool(args.include_historical_versions),
                    "include_creator_global_when_project_scope": bool(args.include_creator_global),
                    "include_creator_global_when_workflow_scope": bool(args.include_creator_global),
                    "max_items": int(args.max_items),
                    "max_items_per_source": int(args.max_items_per_source),
                    "max_items_per_type": int(args.max_items_per_type),
                },
                debug=bool(args.debug),
            )
            if args.json:
                print(_dump(payload), file=stdout)
            else:
                summary = payload["summary"]
                snapshot = payload["snapshot"]
                print(f"Creator: {summary['creator_id']}", file=stdout)
                print(f"Scope: {summary['source_scope']}", file=stdout)
                print(f"Fingerprint: {summary['content_fingerprint']}", file=stdout)
                print(f"Evidence: {summary['evidence_count']}", file=stdout)
                print(f"Categories: {_dump(snapshot['category_counts'])}", file=stdout)
                print(f"Quality: {_dump(snapshot['quality_counts'])}", file=stdout)
                print(f"Excluded: {_dump(snapshot['excluded_counts'])}", file=stdout)
            return 0
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
    raise ValueError("Accion de voice no reconocida.")

