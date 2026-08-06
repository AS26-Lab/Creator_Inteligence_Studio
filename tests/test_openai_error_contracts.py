from __future__ import annotations

import json
import unittest
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRequest
from creator_intelligence_studio.infrastructure.ai_runtime.providers import OpenAIProvider
from tests.ai_runtime_test_support import StrictOpenAIContractFake


def _request() -> AIExecutionRequest:
    return AIExecutionRequest(
        request_id="req-contract",
        task_type="provider_diagnostic",
        operation="extract",
        creator_id=None,
        project_id=None,
        model_role="cheap_structured_model",
        quality_level="standard",
        privacy_class="selected_text_allowed",
        input_data={"status": "ok", "logical_role": "cheap_structured_model", "short_message": "Provider diagnostic completed successfully."},
        context_package={},
        output_contract={"required": ["status", "logical_role", "short_message"]},
        budget={},
        cache_policy="bypass",
        fallback_policy="none",
        approval_policy="not_required",
        metadata={},
    )


class FakeHTTPResponse:
    def __init__(self, status: int, payload: bytes) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class OpenAIErrorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = OpenAIProvider()

    def test_strict_fake_rejects_temperature_before_http(self) -> None:
        fake = StrictOpenAIContractFake(model_id="gpt-5.6-luna")
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(
                {
                    "model": "gpt-5.6-luna",
                    "input": "Reply with the single word OK.",
                    "max_output_tokens": 256,
                    "temperature": 0,
                    "reasoning": {"effort": "none"},
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(HTTPError) as context:
            fake(request, timeout=30.0)

        self.assertEqual(fake.calls, 1)
        self.assertEqual(context.exception.code, 400)
        self.assertIn("temperature", context.exception.read().decode("utf-8"))

    def test_strict_fake_rejects_missing_reasoning_on_responses_contract(self) -> None:
        fake = StrictOpenAIContractFake(model_id="gpt-5.6-luna")
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(
                {
                    "model": "gpt-5.6-luna",
                    "input": "Reply with the single word OK.",
                    "max_output_tokens": 256,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(HTTPError) as context:
            fake(request, timeout=30.0)

        self.assertEqual(context.exception.code, 400)
        self.assertIn("reasoning", context.exception.read().decode("utf-8"))

    def test_http_error_mapping_covers_representative_openai_failures(self) -> None:
        cases = [
            (401, {"error": {"message": "invalid api key sk-secret", "type": "invalid_api_key"}}, "authentication_error", "invalid_api_key"),
            (403, {"error": {"message": "billing disabled", "type": "billing"}}, "billing_error", "billing"),
            (404, {"error": {"message": "model does not exist", "type": "model_not_found"}}, "model_unavailable", "model_not_found"),
            (429, {"error": {"message": "rate limit exceeded", "type": "rate_limit"}}, "rate_limit_error", "rate_limit"),
            (500, {"error": {"message": "server error", "type": "server_error"}}, "provider_error", "server_error"),
        ]
        for status, payload, expected_category, expected_code in cases:
            with self.subTest(status=status):
                error = HTTPError(
                    "https://api.openai.com/v1/responses",
                    status,
                    "error",
                    hdrs=None,
                    fp=BytesIO(json.dumps(payload).encode("utf-8")),
                )

                with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=error):
                    response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-5.6-luna", prompt_text='{"status":"ok"}')

                self.assertIsNotNone(response.error)
                self.assertEqual(response.error.category, expected_category)
                self.assertEqual(response.error.provider_code, expected_code)
                self.assertNotIn("sk-secret", response.error.safe_message)

    def test_invalid_json_and_empty_response_are_rejected(self) -> None:
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, b"not json")):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-5.6-luna", prompt_text='{"status":"ok"}')
        self.assertEqual(response.error.category, "invalid_response")

        empty_payload = {
            "id": "resp-empty",
            "object": "response",
            "status": "completed",
            "model": "gpt-5.6-luna",
            "output": [],
            "usage": {"input_tokens": 70, "output_tokens": 64},
        }
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(empty_payload).encode("utf-8"))):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-5.6-luna", prompt_text="Reply with the single word OK.")
        self.assertIsNone(response.error)
        self.assertEqual(response.response_status, "completed")
        self.assertEqual(response.response_state, "empty")


if __name__ == "__main__":
    unittest.main()
