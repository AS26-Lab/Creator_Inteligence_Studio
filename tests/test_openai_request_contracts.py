from __future__ import annotations

import unittest

from creator_intelligence_studio.infrastructure.ai_runtime.request_profiles import (
    build_openai_diagnostic_payload,
    describe_openai_request_payload,
    resolve_openai_request_profile,
    validate_openai_request,
)


class OpenAIRequestContractTests(unittest.TestCase):
    def test_gpt_5_6_luna_minimal_payload_uses_responses_contract(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")
        payload = build_openai_diagnostic_payload(
            profile=profile,
            model_id="gpt-5.6-luna",
            prompt_text="Reply with the single word OK.",
        )

        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(profile.endpoint, "responses")
        self.assertEqual(profile.output_token_parameter, "max_output_tokens")
        self.assertEqual(payload["input"], "Reply with the single word OK.")
        self.assertEqual(payload["max_output_tokens"], 256)
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertNotIn("temperature", payload)
        self.assertNotIn("messages", payload)
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("max_completion_tokens", payload)
        valid, error = validate_openai_request(payload, profile)
        self.assertTrue(valid, error)

        summary = describe_openai_request_payload(endpoint=profile.endpoint, profile=profile, payload=payload)
        self.assertEqual(summary["fields"]["input"], "redacted:string")
        self.assertEqual(summary["fields"]["max_output_tokens"], "integer")
        self.assertEqual(summary["fields"]["reasoning"], "object")
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
            prompt_text="Reply with the single word OK.",
        )
        payload["temperature"] = 0

        valid, error = validate_openai_request(payload, profile)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertEqual(error["provider_code"], "unsupported_parameter")
        self.assertIn("temperature", str(error["technical_reference"]))

    def test_openai_request_validation_rejects_reasoning_and_endpoint_mismatch(self) -> None:
        profile = resolve_openai_request_profile("gpt-5.6-luna")
        payload = build_openai_diagnostic_payload(
            profile=profile,
            model_id="gpt-5.6-luna",
            prompt_text="Reply with the single word OK.",
        )

        payload_without_reasoning = {key: value for key, value in payload.items() if key != "reasoning"}
        valid, error = validate_openai_request(payload_without_reasoning, profile)
        self.assertFalse(valid)
        self.assertEqual(error["provider_code"], "unsupported_value")

        payload_with_messages = {**payload, "messages": [{"role": "user", "content": "bad"}]}
        valid, error = validate_openai_request(payload_with_messages, profile)
        self.assertFalse(valid)
        self.assertEqual(error["provider_code"], "unsupported_parameter")


if __name__ == "__main__":
    unittest.main()
