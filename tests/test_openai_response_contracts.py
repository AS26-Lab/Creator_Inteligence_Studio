from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRequest
from creator_intelligence_studio.infrastructure.ai_runtime.providers import OpenAIProvider
from creator_intelligence_studio.infrastructure.ai_runtime.request_profiles import parse_openai_chat_completions_response


def _request() -> AIExecutionRequest:
    return AIExecutionRequest(
        request_id="req-openai-response",
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


class OpenAIResponseContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = OpenAIProvider()

    def test_parser_handles_string_array_refusal_and_truncation_shapes(self) -> None:
        cases = [
            (
                {
                    "model": "gpt-5.6-luna",
                    "choices": [
                        {"message": {"content": " OK. \n"}, "finish_reason": "stop"},
                    ],
                    "usage": {"prompt_tokens": 70, "completion_tokens": 64, "cached_tokens": 0},
                },
                "content",
                "string",
                "OK.",
                70,
                64,
            ),
            (
                {
                    "model": "gpt-5.6-luna",
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "text", "text": " OK. "},
                                    {"type": "text", "text": "Done."},
                                ]
                            },
                            "finish_reason": "stop",
                        },
                    ],
                    "usage": {"prompt_tokens": 70, "completion_tokens": 64, "cached_tokens": 0},
                },
                "content",
                "array",
                "OK.\nDone.",
                70,
                64,
            ),
            (
                {
                    "model": "gpt-5.6-luna",
                    "choices": [
                        {
                            "message": {"content": [], "refusal": "I cannot comply."},
                            "finish_reason": "content_filter",
                        },
                    ],
                    "usage": {"prompt_tokens": 70, "completion_tokens": 64, "cached_tokens": 0},
                },
                "refusal",
                "array",
                "",
                70,
                64,
            ),
            (
                {
                    "model": "gpt-5.6-luna",
                    "choices": [
                        {"message": {"content": ""}, "finish_reason": "length"},
                    ],
                    "usage": {"prompt_tokens": 70, "completion_tokens": 64, "cached_tokens": 0},
                },
                "truncated",
                "string",
                "",
                70,
                64,
            ),
        ]
        for payload, expected_state, expected_shape, expected_text, input_tokens, output_tokens in cases:
            with self.subTest(state=expected_state):
                parsed = parse_openai_chat_completions_response(payload)
                self.assertEqual(parsed["response_state"], expected_state)
                self.assertEqual(parsed["content_shape"], expected_shape)
                self.assertEqual(parsed["output_text"], expected_text)
                self.assertEqual(parsed["usage"]["input_tokens"], input_tokens)
                self.assertEqual(parsed["usage"]["output_tokens"], output_tokens)

    def test_provider_execute_preserves_textual_response_and_usage(self) -> None:
        payload = {
            "model": "gpt-5.6-luna",
            "choices": [
                {
                    "message": {"role": "assistant", "content": " OK. \n"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 70, "completion_tokens": 64, "cached_tokens": 0},
        }

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-5.6-luna", prompt_text="Return a short acknowledgement.")

        self.assertIsNone(response.error)
        self.assertEqual(response.output_text, "OK.")
        self.assertEqual(response.content_shape, "string")
        self.assertEqual(response.content_length, 3)
        self.assertEqual(response.response_state, "content")
        self.assertEqual(response.raw_finish_reason, "stop")
        self.assertEqual(response.usage.input_tokens, 70)
        self.assertEqual(response.usage.output_tokens, 64)

    def test_provider_execute_marks_empty_choices_as_validation_input_not_transport_failure(self) -> None:
        payload = {
            "model": "gpt-5.6-luna",
            "choices": [
                {
                    "message": {"role": "assistant", "content": []},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 70, "completion_tokens": 64, "cached_tokens": 0},
        }

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-5.6-luna", prompt_text="Return a short acknowledgement.")

        self.assertIsNone(response.error)
        self.assertEqual(response.output_text, "")
        self.assertEqual(response.response_state, "empty")
        self.assertEqual(response.usage.input_tokens, 70)
        self.assertEqual(response.usage.output_tokens, 64)

    def test_invalid_response_shape_is_still_rejected(self) -> None:
        payload = {"model": "gpt-5.6-luna", "usage": {"prompt_tokens": 70, "completion_tokens": 64}}
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-5.6-luna", prompt_text="Return a short acknowledgement.")
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error.category, "invalid_response")


if __name__ == "__main__":
    unittest.main()
