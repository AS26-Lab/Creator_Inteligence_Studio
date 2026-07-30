"""Registries for AI models and prompt templates."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from .models import (
    AIBudgetPolicy,
    AIExecutionRequest,
    AIModelCatalogEntry,
    AIModelStatus,
    AIPromptTemplate,
    AIRoleAssignment,
    AIFallbackPolicy,
)
from .repository import SQLiteAIRuntimeRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ModelRegistry:
    def __init__(self, repository: SQLiteAIRuntimeRepository) -> None:
        self.repository = repository

    def list_models(self, provider: str | None = None) -> list[AIModelCatalogEntry]:
        return self.repository.list_model_catalog_entries(provider)

    def get_model(self, model_catalog_id: str) -> AIModelCatalogEntry | None:
        return self.repository.get_model_catalog_entry(model_catalog_id)

    def upsert_model(self, entry: AIModelCatalogEntry) -> AIModelCatalogEntry:
        return self.repository.upsert_model_catalog_entry(entry)

    def list_roles(self, creator_id: str | None = None, provider: str | None = None) -> list[AIRoleAssignment]:
        return self.repository.list_role_assignments(creator_id=creator_id, provider=provider)

    def assign_role(
        self,
        *,
        role: str,
        provider: str,
        model_id: str,
        creator_id: str | None = None,
        display_name: str | None = None,
        is_default: bool = False,
        is_enabled: bool = True,
        fallback_policy: AIFallbackPolicy = "none",
        quality_level: str = "standard",
        status: AIModelStatus = "testing",
        capabilities_json: dict[str, object] | None = None,
        snapshot_or_version: str | None = None,
    ) -> AIRoleAssignment:
        existing_models = [
            entry
            for entry in self.repository.list_model_catalog_entries(provider)
            if entry.model_id == model_id and entry.snapshot_or_version == snapshot_or_version
        ]
        if existing_models:
            model = existing_models[0]
        else:
            model = self.repository.upsert_model_catalog_entry(
                AIModelCatalogEntry(
                    provider=provider,
                    model_id=model_id,
                    display_name=display_name or model_id,
                    snapshot_or_version=snapshot_or_version,
                    status=status,
                    capabilities_json=capabilities_json or {},
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
        assignment = AIRoleAssignment(
            creator_id=creator_id,
            role=role,
            provider=provider,
            model_catalog_id=model.id or model_id,
            quality_level=quality_level,
            is_default=is_default,
            is_enabled=is_enabled,
            fallback_policy=fallback_policy,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        return self.repository.upsert_role_assignment(assignment)

    def resolve_role(
        self,
        role: str,
        *,
        creator_id: str | None = None,
        provider: str | None = None,
    ) -> tuple[AIRoleAssignment, AIModelCatalogEntry] | None:
        assignment = self.repository.resolve_role_assignment(role, creator_id=creator_id, provider=provider)
        if assignment is None:
            return None
        model = self.repository.get_model_catalog_entry(assignment.model_catalog_id)
        if model is None:
            return None
        return assignment, model

    def ensure_template(self, template: AIPromptTemplate) -> AIPromptTemplate:
        return self.repository.upsert_prompt_template(template)

    def get_template(self, template_key: str, version: int | None = None) -> AIPromptTemplate | None:
        return self.repository.get_prompt_template(template_key, version=version)

    def list_templates(self, status: str | None = None) -> list[AIPromptTemplate]:
        return self.repository.list_prompt_templates(status=status)


class PromptRegistry:
    def __init__(self, repository: SQLiteAIRuntimeRepository) -> None:
        self.repository = repository

    def get_approved(self, template_key: str) -> AIPromptTemplate | None:
        return self.repository.get_prompt_template(template_key)

    def ensure_template(self, template: AIPromptTemplate) -> AIPromptTemplate:
        return self.repository.upsert_prompt_template(template)

    def list_templates(self, status: str | None = None) -> list[AIPromptTemplate]:
        return self.repository.list_prompt_templates(status=status)
