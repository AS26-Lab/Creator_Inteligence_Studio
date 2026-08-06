from __future__ import annotations

import unittest

from creator_intelligence_studio.infrastructure.ai_runtime.request_profiles import (
    build_openai_diagnostic_payload,
    describe_openai_request_payload,
    resolve_openai_request_profile,
    validate_openai_request,
)


class OpenAIRequestContractTests(unittest.TestCase):
    def test_gpt_5_6_luna_minimal_payload_omits_incompatible_defaults(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")
        payload = build_openai_diagnostic_payload(
            profile=profile,
            model_id="gpt-5.6-luna",
            prompt_text='{"status":"ok"}',
        )

        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["max_completion_tokens"], 64)
        self.assertNotIn("temperature", payload)
        self.assertNotIn("response_format", payload)
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("max_output_tokens", payload)
        valid, error = validate_openai_request(payload, profile)
        self.assertTrue(valid, error)

        summary = describe_openai_request_payload(endpoint=profile.endpoint, profile=profile, payload=payload)
        self.assertEqual(summary["fields"]["messages"], "redacted:list")
        self.assertEqual(summary["fields"]["max_completion_tokens"], "integer")
        self.assertNotIn("temperature", summary["fields"])

    def test_configurable_openai_profile_allows_explicit_temperature_and_structured_output(self) -> None:
        profile = resolve_openai_request_profile("gpt-4.1-mini")
        payload = build_openai_diagnostic_payload(
            profile=profile,
            model_id="gpt-4.1-mini",
            prompt_text='{"status":"ok"}',
            temperature=0.2,
            include_structured_output=True,
        )

        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        valid, error = validate_openai_request(payload, profile)
        self.assertTrue(valid, error)

    def test_openai_request_validation_rejects_multiple_output_parameters(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")
        payload = build_openai_diagnostic_payload(
            profile=profile,
            model_id="gpt-5.6-luna",
            prompt_text='{"status":"ok"}',
        )
        payload["max_tokens"] = 64

        valid, error = validate_openai_request(payload, profile)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["provider_code"], "unsupported_parameter")

    def test_openai_request_validation_rejects_temperature_for_gpt_5_6(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")
        payload = build_openai_diagnostic_payload(
            profile=profile,
            model_id="gpt-5.6-luna",
            prompt_text='{"status":"ok"}',
        )
        payload["temperature"] = 0

        valid, error = validate_openai_request(payload, profile)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["provider_code"], "unsupported_value")
        self.assertIn("temperature", str(error["technical_reference"]))


if __name__ == "__main__":
    unittest.main()
