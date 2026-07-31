"""CLI para AI Runtime and Provider Orchestration Foundation."""

from __future__ import annotations

import json
from typing import Any

from creator_intelligence_studio.application.services.ai_runtime_service import AIRuntimeService


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


def build_ai_parser(subparsers) -> None:
    parser = subparsers.add_parser("ai", help="AI Runtime and Provider Orchestration Foundation")
    ai_sub = parser.add_subparsers(dest="action", required=True)

    providers = ai_sub.add_parser("providers", help="Proveedores de IA")
    providers_sub = providers.add_subparsers(dest="provider_action", required=True)
    providers_sub.add_parser("list", help="Listar proveedores").add_argument("--json", action="store_true")
    providers_sub.add_parser("status", help="Estado de proveedores").add_argument("--json", action="store_true")
    provider_test = providers_sub.add_parser("test", help="Probar un proveedor")
    provider_test.add_argument("--provider", required=True, choices=["openai", "anthropic"])
    provider_test.add_argument("--json", action="store_true")

    models = ai_sub.add_parser("models", help="Catalogo de modelos")
    models_sub = models.add_subparsers(dest="models_action", required=True)
    models_list = models_sub.add_parser("list", help="Listar modelos")
    models_list.add_argument("--provider", choices=["openai", "anthropic"])
    models_list.add_argument("--json", action="store_true")
    model_verify = models_sub.add_parser("verify", help="Verificar modelos de un proveedor")
    model_verify.add_argument("--provider", required=True, choices=["openai", "anthropic"])
    model_verify.add_argument("--json", action="store_true")

    roles = ai_sub.add_parser("roles", help="Asignaciones por rol")
    roles_sub = roles.add_subparsers(dest="roles_action", required=True)
    roles_sub.add_parser("list", help="Listar roles").add_argument("--json", action="store_true")
    role_assign = roles_sub.add_parser("assign", help="Asignar rol a modelo")
    role_assign.add_argument("--role", required=True)
    role_assign.add_argument("--provider", required=True, choices=["openai", "anthropic"])
    role_assign.add_argument("--model", required=True)
    role_assign.add_argument("--creator-id")
    role_assign.add_argument("--display-name")
    role_assign.add_argument("--default", action="store_true")
    role_assign.add_argument("--enabled", dest="enabled", action="store_true")
    role_assign.add_argument("--disabled", dest="enabled", action="store_false")
    role_assign.set_defaults(enabled=True)
    role_assign.add_argument("--fallback", choices=["none", "provider", "cross_provider"], default="none")
    role_assign.add_argument("--status", choices=["testing", "approved", "deprecated", "unavailable", "blocked"], default="testing")
    role_assign.add_argument("--snapshot")
    role_assign.add_argument("--json", action="store_true")

    budget = ai_sub.add_parser("budget", help="Presupuesto y consumo")
    budget_sub = budget.add_subparsers(dest="budget_action", required=True)
    budget_sub.add_parser("show", help="Mostrar presupuesto").add_argument("--json", action="store_true")
    set_monthly = budget_sub.add_parser("set-monthly", help="Definir limite mensual")
    set_monthly.add_argument("--amount", required=True, type=float)
    set_monthly.add_argument("--currency", required=True)
    set_monthly.add_argument("--json", action="store_true")
    set_per_task = budget_sub.add_parser("set-per-task", help="Definir limite por tarea")
    set_per_task.add_argument("--amount", required=True, type=float)
    set_per_task.add_argument("--currency", required=True)
    set_per_task.add_argument("--json", action="store_true")

    diagnostic = ai_sub.add_parser("diagnostic", help="Diagnostico de IA")
    diagnostic_sub = diagnostic.add_subparsers(dest="diagnostic_action", required=True)
    diagnostic_run = diagnostic_sub.add_parser("run", help="Ejecutar diagnostico")
    diagnostic_run.add_argument("--provider", choices=["openai", "anthropic"])
    diagnostic_run.add_argument("--role")
    diagnostic_run.add_argument("--cache", choices=["use", "bypass", "refresh"], default="use")
    diagnostic_run.add_argument("--json", action="store_true")

    executions = ai_sub.add_parser("executions", help="Historial de ejecuciones")
    executions_sub = executions.add_subparsers(dest="executions_action", required=True)
    executions_list = executions_sub.add_parser("list", help="Listar ejecuciones")
    executions_list.add_argument("--creator-id")
    executions_list.add_argument("--provider", choices=["openai", "anthropic"])
    executions_list.add_argument("--limit", type=int, default=50)
    executions_list.add_argument("--json", action="store_true")
    executions_show = executions_sub.add_parser("show", help="Mostrar ejecucion")
    executions_show.add_argument("execution_id")
    executions_show.add_argument("--json", action="store_true")


def handle_ai_command(args, *, service: AIRuntimeService | None, stdout, stderr) -> int:
    if service is None:
        print("Error: el servicio de IA no esta disponible.", file=stderr)
        return 1
    if args.action == "providers":
        if args.provider_action == "list":
            print(_dump(service.list_providers()), file=stdout)
            return 0
        if args.provider_action == "status":
            print(_dump(service.provider_status()), file=stdout)
            return 0
        if args.provider_action == "test":
            print(_dump(service.test_provider(args.provider).to_dict()), file=stdout)
            return 0
    if args.action == "models":
        if args.models_action == "list":
            print(_dump(service.list_models(args.provider)), file=stdout)
            return 0
        if args.models_action == "verify":
            print(_dump(service.verify_models(args.provider)), file=stdout)
            return 0
    if args.action == "roles":
        if args.roles_action == "list":
            print(_dump(service.list_roles()), file=stdout)
            return 0
        if args.roles_action == "assign":
            try:
                payload = service.assign_role(
                    role=args.role,
                    provider=args.provider,
                    model_id=args.model,
                    creator_id=args.creator_id,
                    display_name=args.display_name,
                    is_default=args.default,
                    is_enabled=args.enabled,
                    fallback_policy=args.fallback,
                    status=args.status,
                    snapshot_or_version=args.snapshot,
                )
            except ValueError as exc:
                print(f"Error: {exc}", file=stderr)
                return 1
            print(_dump(payload), file=stdout)
            return 0
    if args.action == "budget":
        if args.budget_action == "show":
            print(_dump(service.get_budget_policy()), file=stdout)
            return 0
        if args.budget_action == "set-monthly":
            print(_dump(service.set_monthly_budget(args.amount, args.currency)), file=stdout)
            return 0
        if args.budget_action == "set-per-task":
            print(_dump(service.set_per_task_budget(args.amount, args.currency)), file=stdout)
            return 0
    if args.action == "diagnostic":
        if args.diagnostic_action == "run":
            result = service.diagnostic_run(provider=args.provider, role=args.role, cache_policy=args.cache)
            print(_dump(result.to_dict()), file=stdout)
            return 0
    if args.action == "executions":
        if args.executions_action == "list":
            print(_dump(service.list_executions(creator_id=args.creator_id, provider=args.provider, limit=args.limit)), file=stdout)
            return 0
        if args.executions_action == "show":
            print(_dump(service.get_execution(args.execution_id)), file=stdout)
            return 0
    print("Error: comando de IA no reconocido.", file=stderr)
    return 1
