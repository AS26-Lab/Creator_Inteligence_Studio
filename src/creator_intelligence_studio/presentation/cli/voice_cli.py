"""CLI technical surface for Creator Voice evidence and profiles."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any

from creator_intelligence_studio.application.services.creator_voice_evidence_service import CreatorVoiceEvidenceService
from creator_intelligence_studio.application.services.creator_voice_profile_service import (
    CreatorVoiceProfileService,
    build_creator_voice_profile_service,
)
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


def _add_snapshot_arguments(parser: argparse.ArgumentParser, *, prefix: str = "") -> None:
    prefix_name = f"{prefix}-" if prefix else ""
    parser.add_argument(f"--{prefix_name}creator-id", dest=f"{prefix}_creator_id" if prefix else "creator_id", required=True)
    parser.add_argument(f"--{prefix_name}project-id", dest=f"{prefix}_project_id" if prefix else "project_id")
    parser.add_argument(f"--{prefix_name}workflow-type", dest=f"{prefix}_workflow_type" if prefix else "workflow_type")
    parser.add_argument(f"--{prefix_name}language", dest=f"{prefix}_language" if prefix else "language")
    parser.add_argument(
        f"--{prefix_name}include-historical-versions",
        dest=f"{prefix}_include_historical_versions" if prefix else "include_historical_versions",
        action="store_true",
    )
    parser.add_argument(
        f"--{prefix_name}include-creator-global",
        dest=f"{prefix}_include_creator_global" if prefix else "include_creator_global",
        action="store_true",
    )
    parser.add_argument(f"--{prefix_name}max-items", dest=f"{prefix}_max_items" if prefix else "max_items", type=int, default=24)
    parser.add_argument(
        f"--{prefix_name}max-items-per-source",
        dest=f"{prefix}_max_items_per_source" if prefix else "max_items_per_source",
        type=int,
        default=3,
    )
    parser.add_argument(
        f"--{prefix_name}max-items-per-type",
        dest=f"{prefix}_max_items_per_type" if prefix else "max_items_per_type",
        type=int,
        default=8,
    )


def build_voice_parser(subparsers) -> None:
    parser = subparsers.add_parser("voice", help="Evidencia y perfil de Creator Voice")
    voice_sub = parser.add_subparsers(dest="action", required=True)

    evidence = voice_sub.add_parser("evidence-snapshot", help="Construir un snapshot de evidencia de voz")
    _add_snapshot_arguments(evidence)
    evidence.add_argument("--json", action="store_true")
    evidence.add_argument("--debug", action="store_true")

    profile_build = voice_sub.add_parser("profile-build", help="Construir un perfil de Creator Voice")
    _add_snapshot_arguments(profile_build)
    profile_build.add_argument("--json", action="store_true")
    profile_build.add_argument("--debug", action="store_true")

    profile_show = voice_sub.add_parser("profile-show", help="Mostrar un perfil de Creator Voice")
    _add_snapshot_arguments(profile_show)
    profile_show.add_argument("--json", action="store_true")
    profile_show.add_argument("--debug", action="store_true")

    profile_compare = voice_sub.add_parser("profile-compare", help="Comparar dos perfiles de Creator Voice")
    _add_snapshot_arguments(profile_compare, prefix="base")
    _add_snapshot_arguments(profile_compare, prefix="compare")
    profile_compare.add_argument("--json", action="store_true")
    profile_compare.add_argument("--debug", action="store_true")


def _snapshot_request_from_args(args: argparse.Namespace, *, prefix: str = "") -> dict[str, object]:
    prefix_name = f"{prefix}_" if prefix else ""
    return {
        "creator_id": getattr(args, f"{prefix_name}creator_id"),
        "project_id": getattr(args, f"{prefix_name}project_id"),
        "workflow_type": getattr(args, f"{prefix_name}workflow_type"),
        "language": getattr(args, f"{prefix_name}language"),
        "include_historical_versions": bool(getattr(args, f"{prefix_name}include_historical_versions")),
        "include_creator_global_when_project_scope": bool(getattr(args, f"{prefix_name}include_creator_global")),
        "include_creator_global_when_workflow_scope": bool(getattr(args, f"{prefix_name}include_creator_global")),
        "max_items": int(getattr(args, f"{prefix_name}max_items")),
        "max_items_per_source": int(getattr(args, f"{prefix_name}max_items_per_source")),
        "max_items_per_type": int(getattr(args, f"{prefix_name}max_items_per_type")),
    }


def _print_snapshot(payload: dict[str, object], *, stdout) -> None:
    summary = payload["summary"]
    snapshot = payload["snapshot"]
    print(f"Creator: {summary['creator_id']}", file=stdout)
    print(f"Scope: {summary['source_scope']}", file=stdout)
    print(f"Fingerprint: {summary['content_fingerprint']}", file=stdout)
    print(f"Evidence: {summary['evidence_count']}", file=stdout)
    print(f"Categories: {_dump(snapshot['category_counts'])}", file=stdout)
    print(f"Quality: {_dump(snapshot['quality_counts'])}", file=stdout)
    print(f"Excluded: {_dump(snapshot['excluded_counts'])}", file=stdout)


def _print_profile(payload: dict[str, object], *, stdout) -> None:
    summary = payload["summary"]
    profile = payload["profile"]
    print(f"Creator: {summary['creator_id']}", file=stdout)
    print(f"Status: {summary['status']}", file=stdout)
    print(f"Confidence: {summary['confidence_summary']}", file=stdout)
    print(f"Fingerprint: {summary['fingerprint']}", file=stdout)
    print(f"Summary: {profile['summary']}", file=stdout)
    print(f"Sections: {[section['section_key'] for section in profile['sections']]}", file=stdout)
    print(f"Warnings: {_dump(profile['warnings'])}", file=stdout)
    print(f"Limitations: {_dump(profile['limitations'])}", file=stdout)


def handle_voice_command(
    args: argparse.Namespace,
    *,
    service: CreatorVoiceEvidenceService | None = None,
    evidence_service: CreatorVoiceEvidenceService | None = None,
    profile_service: CreatorVoiceProfileService | None = None,
    stdout,
    stderr,
) -> int:
    try:
        resolved_evidence_service = evidence_service or service
        if resolved_evidence_service is None:
            raise DomainError("El servicio de Creator Voice no esta disponible.")
        if profile_service is None:
            profile_service = build_creator_voice_profile_service()
        if args.action == "evidence-snapshot":
            payload = resolved_evidence_service.diagnostics(_snapshot_request_from_args(args), debug=bool(args.debug))
            if args.json:
                print(_dump(payload), file=stdout)
            else:
                _print_snapshot(payload, stdout=stdout)
            return 0
        if args.action in {"profile-build", "profile-show"}:
            snapshot = resolved_evidence_service.build_snapshot(_snapshot_request_from_args(args))
            profile = profile_service.build_profile(snapshot)
            payload = profile_service.diagnostics(profile, debug=bool(args.debug))
            if args.json:
                print(_dump(payload), file=stdout)
            else:
                _print_profile(payload, stdout=stdout)
            return 0
        if args.action == "profile-compare":
            base_snapshot = resolved_evidence_service.build_snapshot(_snapshot_request_from_args(args, prefix="base"))
            compare_snapshot = resolved_evidence_service.build_snapshot(_snapshot_request_from_args(args, prefix="compare"))
            base_profile = profile_service.build_profile(base_snapshot)
            compare_profile = profile_service.build_profile(compare_snapshot)
            comparison = profile_service.compare_profiles(base_profile, compare_profile)
            payload = comparison.to_dict()
            if args.json:
                print(_dump(payload), file=stdout)
            else:
                print(f"Creator: {payload['creator_id']}", file=stdout)
                print(f"Base fingerprint: {payload['base_profile_fingerprint']}", file=stdout)
                print(f"Compare fingerprint: {payload['compare_profile_fingerprint']}", file=stdout)
                print(f"Changed sections: {payload['changed_sections']}", file=stdout)
                print(f"Changed features: {payload['changed_features']}", file=stdout)
                print(f"Summary: {payload['summary']}", file=stdout)
            return 0
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
    raise ValueError("Accion de voice no reconocida.")
