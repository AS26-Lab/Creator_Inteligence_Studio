"""CLI de Market and Trend Intelligence Foundation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from creator_intelligence_studio.application.commands.market_intelligence_commands import (
    BuildMarketReportCommand,
    CreateMarketDefinitionCommand,
    CreateMarketTopicCommand,
    CreateResearchQueryCommand,
    ExportMarketReportCommand,
    ListMarketDefinitionsCommand,
    ListMarketSignalsCommand,
    RegisterMarketSourceCommand,
    RunResearchQueryCommand,
)
from creator_intelligence_studio.application.services.market_intelligence_service import MarketIntelligenceService


def _json_default(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_market_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("market", help="Market and Trend Intelligence Foundation")
    sub = parser.add_subparsers(dest="action", required=True)

    markets = sub.add_parser("markets", help="Listar mercados")
    markets.add_argument("--creator-id", required=True)
    markets.add_argument("--json", action="store_true")

    market_create = sub.add_parser("market-create", help="Crear mercado")
    market_create.add_argument("--creator-id", required=True)
    market_create.add_argument("--name", required=True)
    market_create.add_argument("--description")
    market_create.add_argument("--market-type", default="market")
    market_create.add_argument("--primary-language")
    market_create.add_argument("--primary-region")
    market_create.add_argument("--json", action="store_true")

    market_show = sub.add_parser("market-show", help="Mostrar mercado")
    market_show.add_argument("--market-id", required=True)
    market_show.add_argument("--json", action="store_true")

    topics = sub.add_parser("topics", help="Listar temas")
    topics.add_argument("--creator-id", required=True)
    topics.add_argument("--market-id")
    topics.add_argument("--json", action="store_true")

    topic_create = sub.add_parser("topic-create", help="Crear tema")
    topic_create.add_argument("--creator-id", required=True)
    topic_create.add_argument("--market-id", required=True)
    topic_create.add_argument("--canonical-name", required=True)
    topic_create.add_argument("--display-name")
    topic_create.add_argument("--description")
    topic_create.add_argument("--json", action="store_true")

    sources = sub.add_parser("sources", help="Listar fuentes")
    sources.add_argument("--creator-id", required=True)
    sources.add_argument("--platform")
    sources.add_argument("--json", action="store_true")

    source_add = sub.add_parser("source-add", help="Agregar fuente")
    source_add.add_argument("--creator-id", required=True)
    source_add.add_argument("--source-type", required=True)
    source_add.add_argument("--name", required=True)
    source_add.add_argument("--access-method", required=True)
    source_add.add_argument("--trust-level", required=True)
    source_add.add_argument("--permission-status", default="unknown")
    source_add.add_argument("--enabled", action="store_true")
    source_add.add_argument("--platform")
    source_add.add_argument("--source-identifier")
    source_add.add_argument("--source-url")
    source_add.add_argument("--json", action="store_true")

    queries = sub.add_parser("queries", help="Listar consultas")
    queries.add_argument("--creator-id", required=True)
    queries.add_argument("--market-id")
    queries.add_argument("--json", action="store_true")

    query_create = sub.add_parser("query-create", help="Crear consulta")
    query_create.add_argument("--creator-id", required=True)
    query_create.add_argument("--platform", required=True)
    query_create.add_argument("--query-text")
    query_create.add_argument("--query-type", default="search")
    query_create.add_argument("--market-id")
    query_create.add_argument("--language")
    query_create.add_argument("--region")
    query_create.add_argument("--published-after")
    query_create.add_argument("--published-before")
    query_create.add_argument("--max-results", type=int, default=25)
    query_create.add_argument("--json", action="store_true")

    research_run = sub.add_parser("research-run", help="Ejecutar una consulta")
    research_run.add_argument("--query-id", required=True)
    research_run.add_argument("--json", action="store_true")

    signals = sub.add_parser("signals", help="Listar señales")
    signals.add_argument("--creator-id", required=True)
    signals.add_argument("--market-id")
    signals.add_argument("--json", action="store_true")

    patterns = sub.add_parser("patterns", help="Listar patrones")
    patterns.add_argument("--creator-id", required=True)
    patterns.add_argument("--market-id")
    patterns.add_argument("--json", action="store_true")

    opportunities = sub.add_parser("opportunities", help="Listar oportunidades")
    opportunities.add_argument("--creator-id", required=True)
    opportunities.add_argument("--market-id")
    opportunities.add_argument("--json", action="store_true")

    fit = sub.add_parser("fit", help="Evaluar compatibilidad")
    fit.add_argument("--creator-id", required=True)
    fit.add_argument("--target-type", required=True)
    fit.add_argument("--target-id", required=True)
    fit.add_argument("--topic", action="append", dest="topics")
    fit.add_argument("--platform", action="append", dest="platforms")
    fit.add_argument("--evidence-strength", type=float, default=0.5)
    fit.add_argument("--copying-risk", type=float, default=0.0)
    fit.add_argument("--json", action="store_true")

    review = sub.add_parser("review", help="Registrar revision")
    review.add_argument("--creator-id", required=True)
    review.add_argument("--target-type", required=True)
    review.add_argument("--target-id", required=True)
    review.add_argument("--decision", required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="Generar reporte")
    report.add_argument("--creator-id", required=True)
    report.add_argument("--market-id")
    report.add_argument("--json", action="store_true")

    export_report = sub.add_parser("export-report", help="Exportar reporte")
    export_report.add_argument("--report-id", required=True)
    export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    export_report.add_argument("--json", action="store_true")


def handle_market_command(args: argparse.Namespace, *, service: MarketIntelligenceService, stdout=None, stderr=None) -> int:
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    if args.action == "markets":
        command = ListMarketDefinitionsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_market_definitions(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) if args.json else "\n".join(item["name"] for item in payload), file=stdout)
        return 0
    if args.action == "market-create":
        command = CreateMarketDefinitionCommand(args.creator_id, args.name, args.description, args.market_type, args.primary_language, args.primary_region)
        payload = service.create_market_definition(
            creator_id=command.creator_id,
            name=command.name,
            description=command.description,
            market_type=command.market_type,
            primary_language=command.primary_language,
            primary_region=command.primary_region,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "market-show":
        payload = service.get_market_definition(args.market_id)
        if payload is None:
            print("Mercado no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "topics":
        payload = [item.to_dict() for item in service.list_market_topics(args.creator_id, args.market_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "topic-create":
        command = CreateMarketTopicCommand(args.creator_id, args.market_id, args.canonical_name, args.display_name, args.description)
        payload = service.create_market_topic(
            creator_id=command.creator_id,
            market_id=command.market_id,
            canonical_name=command.canonical_name,
            display_name=command.display_name,
            description=command.description,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sources":
        payload = [item.to_dict() for item in service.list_market_sources(args.creator_id, args.platform)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "source-add":
        command = RegisterMarketSourceCommand(
            args.creator_id,
            args.source_type,
            args.name,
            args.access_method,
            args.trust_level,
            permission_status=args.permission_status,
            enabled=bool(args.enabled),
            platform=args.platform,
            source_identifier=args.source_identifier,
            source_url=args.source_url,
        )
        payload = service.register_market_source(
            creator_id=command.creator_id,
            source_type=command.source_type,
            name=command.name,
            access_method=command.access_method,
            trust_level=command.trust_level,
            permission_status=command.permission_status,
            enabled=command.enabled,
            platform=command.platform,
            source_identifier=command.source_identifier,
            source_url=command.source_url,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "queries":
        payload = [item.to_dict() for item in service.list_research_queries(args.creator_id, args.market_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "query-create":
        command = CreateResearchQueryCommand(
            args.creator_id,
            args.platform,
            args.query_text,
            args.query_type,
            args.market_id,
            args.language,
            args.region,
            args.published_after,
            args.published_before,
            args.max_results,
        )
        payload = service.create_research_query(
            creator_id=command.creator_id,
            platform=command.platform,
            query_text=command.query_text,
            query_type=command.query_type,
            market_id=command.market_id,
            language=command.language,
            region=command.region,
            published_after=command.published_after,
            published_before=command.published_before,
            max_results=command.max_results,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "research-run":
        command = RunResearchQueryCommand(args.query_id)
        payload = service.run_research_query(command.query_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "signals":
        command = ListMarketSignalsCommand(args.creator_id, args.market_id)
        payload = [item.to_dict() for item in service.list_trend_signals(command.creator_id, command.market_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "patterns":
        payload = [item.to_dict() for item in service.list_patterns(args.creator_id, args.market_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "opportunities":
        payload = [item.to_dict() for item in service.list_opportunity_candidates(args.creator_id, args.market_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "fit":
        payload = service.evaluate_creator_market_fit(
            creator_id=args.creator_id,
            target_type=args.target_type,
            target_id=args.target_id,
            market_topics=args.topics or [],
            platform_scope=args.platforms or [],
            evidence_strength=args.evidence_strength,
            copying_risk=args.copying_risk,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "review":
        payload = service.review_target(
            creator_id=args.creator_id,
            target_type=args.target_type,
            target_id=args.target_id,
            decision=args.decision,
            reason=args.reason,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "report":
        command = BuildMarketReportCommand(args.creator_id, args.market_id)
        payload = service.build_market_report(command.creator_id, command.market_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-report":
        command = ExportMarketReportCommand(args.report_id, args.format)
        path = service.export_market_report(command.report_id, command.format)
        payload = {"report_id": command.report_id, "format": command.format, "path": str(path)}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    print("Accion de market no reconocida.", file=stderr)
    return 1

