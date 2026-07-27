"""CLI de Audience Model Foundation."""

from __future__ import annotations

import argparse
import json
import sys

from creator_intelligence_studio.application.commands.audience_commands import (
    ArchiveAudienceSegmentCommand,
    BuildAudienceProfileCommand,
    CompareAudienceProfileCommand,
    CreateAudienceSegmentCommand,
    ExportAudienceCommand,
    ListAudienceAffinitiesCommand,
    ListAudienceContentRolesCommand,
    ListAudienceJourneysCommand,
    ListAudiencePlatformRolesCommand,
    ListAudienceProfileHistoryCommand,
    ListAudienceSegmentsCommand,
    ListAudienceSignalsCommand,
    ReviewAudienceJourneyCommand,
    ReviewAudienceSegmentCommand,
    ShowAudienceAffinityCommand,
    ShowAudienceJourneyCommand,
    ShowAudienceSegmentCommand,
    ShowAudienceSignalCommand,
)
from creator_intelligence_studio.application.services.audience_model_service import AudienceModelService


def _json_default(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_audience_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("audience", help="Modelo de audiencia local")
    sub = parser.add_subparsers(dest="action", required=True)

    profile = sub.add_parser("profile", help="Mostrar o construir perfil")
    profile.add_argument("--creator-id", required=True)
    profile.add_argument("--force", action="store_true")
    profile.add_argument("--json", action="store_true")

    profile_build = sub.add_parser("profile-build", help="Construir perfil")
    profile_build.add_argument("--creator-id", required=True)
    profile_build.add_argument("--force", action="store_true")
    profile_build.add_argument("--json", action="store_true")

    profile_history = sub.add_parser("profile-history", help="Historial de perfiles")
    profile_history.add_argument("--creator-id", required=True)
    profile_history.add_argument("--json", action="store_true")

    profile_compare = sub.add_parser("profile-compare", help="Comparar versiones")
    profile_compare.add_argument("--creator-id", required=True)
    profile_compare.add_argument("--base-version", required=True, type=int)
    profile_compare.add_argument("--compare-version", required=True, type=int)
    profile_compare.add_argument("--json", action="store_true")

    signals = sub.add_parser("signals", help="Listar señales")
    signals.add_argument("--creator-id", required=True)
    signals.add_argument("--platform")
    signals.add_argument("--json", action="store_true")

    signal_show = sub.add_parser("signal-show", help="Mostrar señal")
    signal_show.add_argument("--signal-id", required=True)
    signal_show.add_argument("--json", action="store_true")

    segments = sub.add_parser("segments", help="Listar segmentos")
    segments.add_argument("--creator-id", required=True)
    segments.add_argument("--json", action="store_true")

    segment_create = sub.add_parser("segment-create", help="Crear segmento")
    segment_create.add_argument("--creator-id", required=True)
    segment_create.add_argument("--name", required=True)
    segment_create.add_argument("--segment-type", required=True)
    segment_create.add_argument("--scope", required=True)
    segment_create.add_argument("--description", required=True)
    segment_create.add_argument("--platform")
    segment_create.add_argument("--content-type")
    segment_create.add_argument("--topic")
    segment_create.add_argument("--lifecycle-stage")
    segment_create.add_argument("--json", action="store_true")

    segment_show = sub.add_parser("segment-show", help="Mostrar segmento")
    segment_show.add_argument("--segment-id", required=True)
    segment_show.add_argument("--json", action="store_true")

    segment_review = sub.add_parser("segment-review", help="Revisar segmento")
    segment_review.add_argument("--segment-id", required=True)
    segment_review.add_argument("--decision", required=True)
    segment_review.add_argument("--reason", required=True)
    segment_review.add_argument("--previous-value-json")
    segment_review.add_argument("--new-value-json")
    segment_review.add_argument("--json", action="store_true")

    segment_archive = sub.add_parser("segment-archive", help="Archivar segmento")
    segment_archive.add_argument("--segment-id", required=True)
    segment_archive.add_argument("--json", action="store_true")

    affinities = sub.add_parser("affinities", help="Listar afinidades")
    affinities.add_argument("--creator-id", required=True)
    affinities.add_argument("--json", action="store_true")

    affinity_show = sub.add_parser("affinity-show", help="Mostrar afinidad")
    affinity_show.add_argument("--affinity-id", required=True)
    affinity_show.add_argument("--json", action="store_true")

    journeys = sub.add_parser("journeys", help="Listar journeys")
    journeys.add_argument("--creator-id", required=True)
    journeys.add_argument("--json", action="store_true")

    journey_show = sub.add_parser("journey-show", help="Mostrar journey")
    journey_show.add_argument("--journey-id", required=True)
    journey_show.add_argument("--json", action="store_true")

    journey_review = sub.add_parser("journey-review", help="Revisar journey")
    journey_review.add_argument("--journey-id", required=True)
    journey_review.add_argument("--decision", required=True)
    journey_review.add_argument("--reason", required=True)
    journey_review.add_argument("--previous-value-json")
    journey_review.add_argument("--new-value-json")
    journey_review.add_argument("--json", action="store_true")

    roles = sub.add_parser("platform-roles", help="Roles de plataforma")
    roles.add_argument("--creator-id", required=True)
    roles.add_argument("--json", action="store_true")

    content_roles = sub.add_parser("content-roles", help="Roles de contenido")
    content_roles.add_argument("--creator-id", required=True)
    content_roles.add_argument("--json", action="store_true")

    export = sub.add_parser("export", help="Exportar modelo de audiencia")
    export.add_argument("--creator-id", required=True)
    export.add_argument("--format", required=True)
    export.add_argument("--json", action="store_true")


def handle_audience(args: argparse.Namespace, *, service: AudienceModelService, stdout=None, stderr=None) -> int:
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    if args.action in {"profile", "profile-build"}:
        command = BuildAudienceProfileCommand(args.creator_id, force=bool(getattr(args, "force", False)))
        result = service.build_profile(command.creator_id, force=command.force)
        if getattr(args, "json", False):
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print(result.profile.summary, file=stdout)
        return 0
    if args.action == "profile-history":
        command = ListAudienceProfileHistoryCommand(args.creator_id)
        payload = [item.to_dict() for item in service.get_profile_history(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) if getattr(args, "json", False) else "\n".join(item["snapshot_json"] for item in payload), file=stdout)
        return 0
    if args.action == "profile-compare":
        command = CompareAudienceProfileCommand(args.creator_id, args.base_version, args.compare_version)
        payload = service.compare_profiles(command.creator_id, command.base_version, command.compare_version)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "signals":
        command = ListAudienceSignalsCommand(args.creator_id, platform=args.platform)
        payload = [item.to_dict() for item in service.list_signals(command.creator_id, platform=command.platform)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "signal-show":
        command = ShowAudienceSignalCommand(args.signal_id)
        payload = service.get_signal(command.signal_id)
        if payload is None:
            print("Signal no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "segments":
        command = ListAudienceSegmentsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_segments(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "segment-create":
        command = CreateAudienceSegmentCommand(
            args.creator_id,
            args.name,
            args.segment_type,
            args.scope,
            args.description,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            lifecycle_stage=args.lifecycle_stage,
        )
        payload = service.create_segment(
            creator_id=command.creator_id,
            name=command.name,
            segment_type=command.segment_type,
            scope=command.scope,
            description=command.description,
            platform=command.platform,
            content_type=command.content_type,
            topic=command.topic,
            lifecycle_stage=command.lifecycle_stage,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "segment-show":
        command = ShowAudienceSegmentCommand(args.segment_id)
        payload = service.get_segment(command.segment_id)
        if payload is None:
            print("Segmento no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "segment-review":
        command = ReviewAudienceSegmentCommand(
            args.segment_id,
            args.decision,
            args.reason,
            previous_value_json=args.previous_value_json,
            new_value_json=args.new_value_json,
        )
        payload = service.review_segment(
            command.segment_id,
            command.decision,
            command.reason,
            previous_value_json=command.previous_value_json,
            new_value_json=command.new_value_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "segment-archive":
        command = ArchiveAudienceSegmentCommand(args.segment_id)
        payload = service.archive_segment(command.segment_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "affinities":
        command = ListAudienceAffinitiesCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_affinities(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "affinity-show":
        command = ShowAudienceAffinityCommand(args.affinity_id)
        payload = service.get_affinity(command.affinity_id)
        if payload is None:
            print("Affinity no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "journeys":
        command = ListAudienceJourneysCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_journeys(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "journey-show":
        command = ShowAudienceJourneyCommand(args.journey_id)
        payload = service.get_journey(command.journey_id)
        if payload is None:
            print("Journey no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "journey-review":
        command = ReviewAudienceJourneyCommand(
            args.journey_id,
            args.decision,
            args.reason,
            previous_value_json=args.previous_value_json,
            new_value_json=args.new_value_json,
        )
        payload = service.review_journey(
            command.journey_id,
            command.decision,
            command.reason,
            previous_value_json=command.previous_value_json,
            new_value_json=command.new_value_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "platform-roles":
        command = ListAudiencePlatformRolesCommand(args.creator_id)
        payload = service.list_platform_roles(command.creator_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "content-roles":
        command = ListAudienceContentRolesCommand(args.creator_id)
        payload = service.list_content_roles(command.creator_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export":
        command = ExportAudienceCommand(args.creator_id, args.format)
        path = service.export(command.creator_id, command.format)
        print(json.dumps({"creator_id": command.creator_id, "format": command.format, "path": str(path)}, ensure_ascii=False, indent=2), file=stdout)
        return 0
    print("Accion de audience no reconocida.", file=stderr)
    return 1
