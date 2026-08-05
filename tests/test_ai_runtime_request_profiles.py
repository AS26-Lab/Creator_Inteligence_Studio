from __future__ import annotations

import json
import unittest

from creator_intelligence_studio.infrastructure.ai_runtime.request_profiles import (
    build_openai_diagnostic_payload,
    resolve_anthropic_request_profile,
    resolve_openai_request_profile,
    resolve_provider_request_profile,
)


class AIRequestProfileTests(unittest.TestCase):
    def test_openai_gpt_5_6_luna_profile_uses_chat_completions_and_max_completion_tokens(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")

        self.assertEqual(profile.provider, "openai")
        self.assertEqual(profile.endpoint, "chat/completions")
        self.assertEqual(profile.output_token_parameter, "max_completion_tokens")
        self.assertTrue(profile.capabilities.supports_structured_output)
        self.assertTrue(profile.capabilities.supports_reasoning_parameters)
        self.assertTrue(profile.capabilities.supports_tools)
        self.assertEqual(profile.model_family, "gpt-5.6")
        self.assertEqual(profile.source_identifier, "https://developers.openai.com/api/docs/models/gpt-5.6-luna")

        payload = build_openai_diagnostic_payload(profile=profile, model_id="gpt-5.6-luna", prompt_text='{"status":"ok"}')
        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["max_completion_tokens"], 128)
        self.assertNotIn("max_tokens", payload)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["temperature"], 0)

    def test_openai_profile_resolution_is_centralized_for_current_families(self) -> None:
        for model_id in ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.1", "gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"):
            with self.subTest(model_id=model_id):
                profile = resolve_provider_request_profile("openai", model_id)
                self.assertEqual(profile.provider, "openai")
                self.assertEqual(profile.endpoint, "chat/completions")
                self.assertEqual(profile.output_token_parameter, "max_completion_tokens")
                self.assertTrue(profile.capabilities.supports_temperature)

    def test_anthropic_profile_resolves_messages_endpoint(self) -> None:
        profile = resolve_anthropic_request_profile("claude-3-5-sonnet")

        self.assertEqual(profile.provider, "anthropic")
        self.assertEqual(profile.endpoint, "messages")
        self.assertEqual(profile.output_token_parameter, "max_tokens")
        self.assertTrue(profile.capabilities.supports_structured_output)
        self.assertTrue(profile.capabilities.supports_tools)
        self.assertEqual(profile.source_identifier, "https://docs.anthropic.com/")


if __name__ == "__main__":
    unittest.main()
