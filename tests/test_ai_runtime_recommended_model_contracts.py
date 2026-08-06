from __future__ import annotations

import unittest

from creator_intelligence_studio.application.services.ai_runtime_recommendations import RecommendedModelResolver
from creator_intelligence_studio.infrastructure.ai_runtime.models import AIModelCatalogEntry
from creator_intelligence_studio.infrastructure.ai_runtime.request_profiles import build_openai_diagnostic_payload, resolve_openai_request_profile, validate_openai_request


class AIRuntimeRecommendedModelContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = RecommendedModelResolver()
        self.catalog = [
            AIModelCatalogEntry(
                provider="openai",
                model_id="gpt-5.6-luna",
                display_name="GPT-5.6 Luna",
                snapshot_or_version="2026-08-01",
                status="approved",
                capabilities_json={"structured_output": True, "image_input": True},
                context_limit=128000,
                supports_structured_output=True,
                supports_image_input=True,
                supports_audio_input=False,
                input_price_per_million=1.0,
                output_price_per_million=1.0,
                cached_input_price_per_million=0.1,
                pricing_currency="USD",
                pricing_effective_at="2026-08-01T00:00:00Z",
                last_verified_at="2026-08-01T00:00:00Z",
            ),
            AIModelCatalogEntry(
                provider="openai",
                model_id="gpt-4.1-mini",
                display_name="GPT-4.1 mini",
                snapshot_or_version="2026-07-15",
                status="approved",
                capabilities_json={"structured_output": True},
                context_limit=128000,
                supports_structured_output=True,
                supports_image_input=False,
                supports_audio_input=False,
                input_price_per_million=0.8,
                output_price_per_million=0.8,
                cached_input_price_per_million=0.08,
                pricing_currency="USD",
                pricing_effective_at="2026-07-15T00:00:00Z",
                last_verified_at="2026-08-01T00:00:00Z",
            ),
            AIModelCatalogEntry(
                provider="openai",
                model_id="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                snapshot_or_version="legacy",
                status="deprecated",
                capabilities_json={},
                context_limit=16384,
                supports_structured_output=False,
                supports_image_input=False,
                supports_audio_input=False,
                input_price_per_million=None,
                output_price_per_million=None,
                cached_input_price_per_million=None,
                pricing_currency="USD",
                pricing_effective_at=None,
                last_verified_at="2026-08-01T00:00:00Z",
            ),
        ]

    def test_recommended_roles_resolve_to_contract_valid_openai_profiles(self) -> None:
        for role in ("cheap_structured_model", "general_reasoning_model", "creative_writing_model", "evaluation_model", "multimodal_model", "transcription_fallback_model"):
            with self.subTest(role=role):
                recommendation = self.resolver.recommend_role(provider="openai", role=role, catalog=self.catalog, profile_key="equilibrado")
                if recommendation.proposed_model is None:
                    self.assertIn(recommendation.compatibility_state, {"compatibility_unknown", "incompatible_confirmed"})
                    continue
                model_id = str(recommendation.proposed_model["model_id"])
                profile = resolve_openai_request_profile(model_id)
                payload = build_openai_diagnostic_payload(profile=profile, model_id=model_id, prompt_text='{"status":"ok"}')
                valid, error = validate_openai_request(payload, profile)
                self.assertTrue(valid, error)
                if profile.endpoint == "responses":
                    self.assertEqual(profile.output_token_parameter, "max_output_tokens")
                    self.assertEqual(payload["reasoning"], {"effort": "none"})
                    self.assertEqual(payload["max_output_tokens"], 256)
                else:
                    self.assertEqual(profile.output_token_parameter, "max_completion_tokens")
                self.assertIn(profile.temperature_policy, {"omit", "configurable"})

    def test_unknown_openai_model_does_not_become_auto_recommendation(self) -> None:
        recommendation = self.resolver.recommend_role(
            provider="openai",
            role="cheap_structured_model",
            catalog=[
                AIModelCatalogEntry(
                    provider="openai",
                    model_id="gpt-5.6-luna-preview",
                    display_name="GPT-5.6 Luna Preview",
                    snapshot_or_version="2026-08-01",
                    status="testing",
                    capabilities_json={"structured_output": True},
                    context_limit=128000,
                    supports_structured_output=True,
                    supports_image_input=True,
                    supports_audio_input=False,
                    input_price_per_million=1.0,
                    output_price_per_million=1.0,
                    cached_input_price_per_million=0.1,
                    pricing_currency="USD",
                    pricing_effective_at="2026-08-01T00:00:00Z",
                    last_verified_at="2026-08-01T00:00:00Z",
                )
            ],
            profile_key="equilibrado",
        )
        self.assertIsNone(recommendation.proposed_model)
        self.assertEqual(recommendation.compatibility_state, "compatibility_unknown")


if __name__ == "__main__":
    unittest.main()
