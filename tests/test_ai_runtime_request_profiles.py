from __future__ import annotations

import json
import unittest

from creator_intelligence_studio.infrastructure.ai_runtime.request_profiles import (
    describe_openai_request_payload,
    build_openai_diagnostic_payload,
    resolve_anthropic_request_profile,
    resolve_openai_request_profile,
    resolve_provider_request_profile,
    validate_openai_request,
)


class AIRequestProfileTests(unittest.TestCase):
    def test_openai_gpt_5_6_luna_profile_uses_responses_and_max_output_tokens(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")

        self.assertEqual(profile.provider, "openai")
        self.assertEqual(profile.endpoint, "responses")
        self.assertEqual(profile.output_token_parameter, "max_output_tokens")
        self.assertEqual(profile.temperature_policy, "omit")
        self.assertEqual(profile.structured_output_policy, "opt_in")
        self.assertEqual(profile.reasoning_policy, "fixed_none")
        self.assertEqual(profile.status, "verified")
        self.assertEqual(profile.stability, "approved")
        self.assertEqual(profile.catalog_version, profile.version)
        self.assertTrue(profile.capabilities.supports_structured_output)
        self.assertTrue(profile.capabilities.supports_reasoning_parameters)
        self.assertTrue(profile.capabilities.supports_tools)
        self.assertEqual(profile.model_family, "gpt-5.6")
        self.assertEqual(profile.source_identifier, "https://developers.openai.com/api/docs/models/gpt-5.6-luna")

        payload = build_openai_diagnostic_payload(profile=profile, model_id="gpt-5.6-luna", prompt_text="Reply with the single word OK.")
        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["input"], "Reply with the single word OK.")
        self.assertEqual(payload["max_output_tokens"], 256)
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("temperature", payload)
        valid, error = validate_openai_request(payload, profile)
        self.assertTrue(valid, error)
        summary = describe_openai_request_payload(endpoint=profile.endpoint, profile=profile, payload=payload)
        self.assertEqual(summary["endpoint"], "responses")
        self.assertEqual(summary["method"], "POST")
        self.assertEqual(summary["profile"], profile.profile_id)
        self.assertEqual(summary["profile_version"], profile.version)
        self.assertEqual(summary["status"], profile.status)
        self.assertEqual(summary["fields"]["input"], "redacted:string")
        self.assertEqual(summary["fields"]["max_output_tokens"], "integer")
        self.assertEqual(summary["fields"]["reasoning"], "object")

        self.assertEqual(profile.capabilities.supports_image_input, True)
        self.assertEqual(profile.capabilities.supports_audio_input, False)

    def test_openai_gpt_5_6_luna_rejects_temperature_and_unknown_output_parameters(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")
        payload = build_openai_diagnostic_payload(profile=profile, model_id="gpt-5.6-luna", prompt_text="Reply with the single word OK.")

        payload_with_temperature = {**payload, "temperature": 0}
        valid, error = validate_openai_request(payload_with_temperature, profile)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["provider_code"], "unsupported_parameter")
        self.assertIn("temperature", str(error["technical_reference"]))

        payload_with_extra_output = {**payload, "max_tokens": 64}
        valid, error = validate_openai_request(payload_with_extra_output, profile)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["provider_code"], "unsupported_parameter")

    def test_openai_profile_resolution_is_centralized_for_current_families(self) -> None:
        for model_id in ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.1", "gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"):
            with self.subTest(model_id=model_id):
                profile = resolve_provider_request_profile("openai", model_id)
                self.assertEqual(profile.provider, "openai")
                self.assertIn(profile.endpoint, {"chat/completions", "responses"})
                if profile.endpoint == "responses":
                    self.assertEqual(profile.output_token_parameter, "max_output_tokens")
                else:
                    self.assertEqual(profile.output_token_parameter, "max_completion_tokens")
                self.assertIn(profile.temperature_policy, {"omit", "configurable"})
                self.assertIn(profile.status, {"verified", "provisional"})

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
