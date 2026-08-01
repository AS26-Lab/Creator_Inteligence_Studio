from __future__ import annotations

import unittest

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIRoleAssignment
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture
from tests.test_ai_runtime_model_selection import build_role_catalog


class AIRuntimeGuidedConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture(provider="anthropic")
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai", discovered_models=build_role_catalog())
        self.fixture.service.refresh_provider_models("openai")

    def test_guided_summary_prefers_balanced_profile_and_required_role(self) -> None:
        summary = self.fixture.service.guided_configuration_summary("openai", profile_key="equilibrado")
        self.assertEqual(summary["profile_label"], "Equilibrado")
        self.assertEqual(summary["profile_key"], "equilibrado")
        self.assertEqual(len(summary["roles"]), 6)
        self.assertGreaterEqual(summary["recommended_count"], 3)
        cheap = next(role for role in summary["roles"] if role["role"] == "cheap_structured_model")
        self.assertTrue(cheap["required_now"])
        self.assertIsNotNone(cheap["proposed_model"])
        self.assertNotEqual(cheap["proposed_model"]["model_id"], "gpt-3.5-turbo")
        self.assertIn(
            cheap["compatibility_state"],
            {"compatible_verified_catalog", "compatible_by_verified_catalog"},
        )

    def test_unknown_models_stay_unknown_and_do_not_become_incompatible(self) -> None:
        summary = self.fixture.service.list_model_selection("openai", "general_reasoning_model")
        unknown_rows = [row for row in summary["items"] if row.get("compatibility_state") == "compatibility_unknown"]
        self.assertGreater(len(unknown_rows), 0)
        self.assertTrue(all(not row.get("is_incompatible") for row in unknown_rows))

    def test_old_assignment_is_warned_and_preserved_when_not_replacing(self) -> None:
        models = self.fixture.repository.list_model_catalog_entries("openai")
        gpt35 = next(model for model in models if model.model_id == "gpt-3.5-turbo")
        self.fixture.repository.upsert_role_assignment(
            AIRoleAssignment(
                role="cheap_structured_model",
                provider="openai",
                model_catalog_id=gpt35.id or gpt35.model_id,
                quality_level="standard",
                is_default=True,
                is_enabled=True,
            )
        )
        summary = self.fixture.service.guided_configuration_summary("openai", profile_key="equilibrado")
        self.assertEqual(summary["current_assignment_warning"], "Esta asignacion no esta recomendada.")
        applied = self.fixture.service.apply_recommended_configuration(
            "openai",
            profile_key="equilibrado",
            replace_existing=False,
        )
        self.assertGreaterEqual(applied["skipped_count"], 1)
        assignment = self.fixture.repository.resolve_role_assignment("cheap_structured_model", provider="openai")
        self.assertIsNotNone(assignment)
        model = self.fixture.repository.get_model_catalog_entry(assignment.model_catalog_id)
        self.assertIsNotNone(model)
        self.assertEqual(model.model_id, "gpt-3.5-turbo")

    def test_apply_recommended_configuration_resolves_diagnostic_role(self) -> None:
        applied = self.fixture.service.apply_recommended_configuration("openai", profile_key="equilibrado", replace_existing=True)
        self.assertGreaterEqual(applied["applied_count"], 1)
        result = self.fixture.service.diagnostic_run(provider="openai", role="cheap_structured_model")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.model_role, "cheap_structured_model")
        self.assertNotEqual(result.model_id, "gpt-3.5-turbo")


if __name__ == "__main__":
    unittest.main()
