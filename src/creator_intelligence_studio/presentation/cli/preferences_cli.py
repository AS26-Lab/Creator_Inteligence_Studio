"""CLI tecnica para synthesis y confirmacion de preferencias."""

from __future__ import annotations

import argparse
import json
from typing import Any

from creator_intelligence_studio.application.services.creator_preference_synthesis_service import CreatorPreferenceSynthesisService
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


def build_preferences_parser(subparsers) -> None:
    parser = subparsers.add_parser("preferences", help="Sugerencias y preferencias confirmadas")
    prefs = parser.add_subparsers(dest="action", required=True)

    audit = prefs.add_parser("audit-signals", help="Mostrar la matriz de señales soportadas")
    audit.add_argument("--json", action="store_true")

    synthesize = prefs.add_parser("synthesize", help="Reconstruir sugerencias desde learning signals")
    synthesize.add_argument("--creator-id", required=True)
    synthesize.add_argument("--json", action="store_true")

    list_candidates = prefs.add_parser("list-candidates", help="Listar sugerencias de preferencia")
    list_candidates.add_argument("--creator-id", required=True)
    list_candidates.add_argument("--project-id")
    list_candidates.add_argument("--workflow-type")
    list_candidates.add_argument("--status")
    list_candidates.add_argument("--preference-type")
    list_candidates.add_argument("--json", action="store_true")

    confirm = prefs.add_parser("confirm", help="Confirmar una sugerencia")
    confirm.add_argument("--candidate-id", required=True)
    confirm.add_argument("--confirmed-by", default="cli")
    confirm.add_argument("--edited-value")
    confirm.add_argument("--json", action="store_true")

    dismiss = prefs.add_parser("dismiss", help="Descartar una sugerencia")
    dismiss.add_argument("--candidate-id", required=True)
    dismiss.add_argument("--dismissed-by", default="cli")
    dismiss.add_argument("--reason", required=True)
    dismiss.add_argument("--json", action="store_true")

    list_confirmed = prefs.add_parser("list-confirmed", help="Listar preferencias confirmadas")
    list_confirmed.add_argument("--creator-id", required=True)
    list_confirmed.add_argument("--project-id")
    list_confirmed.add_argument("--workflow-type")
    list_confirmed.add_argument("--preference-type")
    list_confirmed.add_argument("--active", choices=["true", "false"])
    list_confirmed.add_argument("--json", action="store_true")

    deactivate = prefs.add_parser("deactivate", help="Desactivar una preferencia confirmada")
    deactivate.add_argument("--preference-id", required=True)
    deactivate.add_argument("--json", action="store_true")

    reactivate = prefs.add_parser("reactivate", help="Reactivar una preferencia confirmada")
    reactivate.add_argument("--preference-id", required=True)
    reactivate.add_argument("--json", action="store_true")

    snapshot = prefs.add_parser("snapshot", help="Mostrar una instantanea de preferencias")
    snapshot.add_argument("--creator-id", required=True)
    snapshot.add_argument("--json", action="store_true")


def handle_preferences_command(
    args: argparse.Namespace,
    *,
    service: CreatorPreferenceSynthesisService,
    stdout,
    stderr,
) -> int:
    try:
        if args.action == "audit-signals":
            payload = service.audit_supported_signal_matrix()
            if args.json:
                print(_dump({"matrix": payload}), file=stdout)
            else:
                for row in payload:
                    print(f"{row['signal_type']}: {row['safe_human_wording']}", file=stdout)
            return 0
        if args.action == "synthesize":
            payload = [candidate.to_dict() for candidate in service.rebuild_candidates(args.creator_id)]
            print(_dump({"candidates": payload}), file=stdout)
            return 0
        if args.action == "list-candidates":
            payload = [
                candidate.to_dict()
                for candidate in service.list_candidates(
                    args.creator_id,
                    project_id=args.project_id,
                    workflow_type=args.workflow_type,
                    status=args.status,
                    preference_type=args.preference_type,
                )
            ]
            print(_dump({"candidates": payload}), file=stdout)
            return 0
        if args.action == "confirm":
            preference = service.confirm_candidate(args.candidate_id, confirmed_by=args.confirmed_by, edited_value=args.edited_value)
            print(_dump({"preference": preference.to_dict()}), file=stdout)
            return 0
        if args.action == "dismiss":
            candidate = service.dismiss_candidate(args.candidate_id, dismissed_by=args.dismissed_by, reason=args.reason)
            print(_dump({"candidate": candidate.to_dict()}), file=stdout)
            return 0
        if args.action == "list-confirmed":
            active = None if args.active is None else args.active == "true"
            payload = [
                preference.to_dict()
                for preference in service.list_confirmed_preferences(
                    args.creator_id,
                    project_id=args.project_id,
                    workflow_type=args.workflow_type,
                    active=active,
                    preference_type=args.preference_type,
                )
            ]
            print(_dump({"preferences": payload}), file=stdout)
            return 0
        if args.action == "deactivate":
            preference = service.deactivate_preference(args.preference_id)
            if preference is None:
                raise DomainError("La preferencia no existe.")
            print(_dump({"preference": preference.to_dict()}), file=stdout)
            return 0
        if args.action == "reactivate":
            preference = service.reactivate_preference(args.preference_id)
            if preference is None:
                raise DomainError("La preferencia no existe.")
            print(_dump({"preference": preference.to_dict()}), file=stdout)
            return 0
        if args.action == "snapshot":
            snapshot = service.preference_snapshot(args.creator_id)
            print(_dump(snapshot.to_dict()), file=stdout)
            return 0
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
    raise ValueError("Accion de preferences no reconocida.")
