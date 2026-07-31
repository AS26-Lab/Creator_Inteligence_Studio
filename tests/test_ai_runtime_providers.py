from __future__ import annotations

from io import BytesIO
import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRequest
from creator_intelligence_studio.infrastructure.ai_runtime.providers import AnthropicProvider, OpenAIProvider


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


def _request() -> AIExecutionRequest:
    return AIExecutionRequest(
        request_id="req-1",
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
        cache_policy="use",
        fallback_policy="none",
        approval_policy="not_required",
        metadata={},
    )


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = OpenAIProvider()

    def test_execute_uses_expected_http_contract(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            payload = {
                "model": "gpt-4.1-mini",
                "choices": [{"message": {"content": '{"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7, "cached_tokens": 2},
            }
            return FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake_urlopen):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-4.1-mini", prompt_text='{"status":"ok"}')

        req = captured["request"]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer sk-openai-test")
        self.assertEqual(captured["timeout"], 30.0)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["model"], "gpt-4.1-mini")
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(response.output_text, '{"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"}')
        self.assertEqual(response.usage.input_tokens, 12)
        self.assertEqual(response.usage.cached_input_tokens, 2)

    def test_test_credentials_uses_expected_http_contract(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeHTTPResponse(200, b'{"data":[{"id":"model-1"}]}')

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake_urlopen):
            diagnostic = self.provider.test_credentials("sk-openai-test")

        req = captured["request"]
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, "https://api.openai.com/v1/models")
        self.assertEqual(req.get_header("Authorization"), "Bearer sk-openai-test")
        self.assertEqual(captured["timeout"], 20.0)
        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(diagnostic.usage["models"], 1)

    def test_error_mapping_and_sanitization(self) -> None:
        cases = [
            (401, {"error": {"message": "invalid api key sk-test-secret", "type": "invalid_api_key"}}, "authentication_error"),
            (403, {"error": {"message": "billing disabled", "type": "billing"}}, "billing_error"),
            (429, {"error": {"message": "rate limit exceeded", "type": "rate_limit"}}, "rate_limit_error"),
            (404, {"error": {"message": "model does not exist", "type": "model_not_found"}}, "model_unavailable"),
        ]
        for status, payload, expected_category in cases:
            with self.subTest(status=status):
                error = HTTPError(
                    "https://api.openai.com/v1/chat/completions",
                    status,
                    "error",
                    hdrs=None,
                    fp=BytesIO(json.dumps(payload).encode("utf-8")),
                )

                def fake_urlopen(request, timeout):
                    raise error

                with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake_urlopen):
                    response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="missing-model", prompt_text='{"status":"ok"}')

                self.assertIsNotNone(response.error)
                self.assertEqual(response.error.category, expected_category)
                self.assertNotIn("sk-test-secret", response.error.safe_message)

    def test_network_timeout_and_connection_errors_are_safe(self) -> None:
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=TimeoutError("socket timeout sk-openai-secret")):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-4.1-mini", prompt_text='{"status":"ok"}')
        self.assertEqual(response.error.category, "timeout")
        self.assertNotIn("sk-openai-secret", response.error.safe_message)

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=URLError("dns failure")):
            response = self.provider.test_credentials("sk-openai-test")
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.error["category"], "network_error")

    def test_malformed_and_usage_optional_responses(self) -> None:
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, b"not json")):
            diagnostic = self.provider.test_credentials("sk-openai-test")
        self.assertEqual(diagnostic.status, "failed")
        self.assertEqual(diagnostic.error["category"], "invalid_response")

        payload = {
            "model": "gpt-4.1-mini",
            "choices": [{"message": {"content": '{"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"}'}}],
        }
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            response = self.provider.execute(_request(), api_key="sk-openai-test", model_id="gpt-4.1-mini", prompt_text='{"status":"ok"}')
        self.assertIsNone(response.error)
        self.assertEqual(response.usage.input_tokens, 0)
        self.assertEqual(response.usage.output_tokens, 0)

    def test_discover_models_normalizes_catalog_and_reports_errors(self) -> None:
        payload = {
            "data": [
                {"id": "gpt-4.1-mini", "display_name": "GPT-4.1 mini", "context_length": 128000},
                {"id": "gpt-4.1-mini", "display_name": "GPT-4.1 mini duplicate"},
                {"id": "text-embedding-3-small", "display_name": "Embedding Small"},
                {"id": "gpt-4o-audio-preview", "display_name": "GPT-4o audio preview", "snapshot": "2026-07-01", "context_length": 128000},
            ]
        }
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            report = self.provider.discover_models("sk-openai-test")
        self.assertEqual(report.status, "ok")
        self.assertEqual(report.found_count, 3)
        self.assertEqual(report.compatible_count, 2)
        models = {model.model_id: model for model in report.models}
        self.assertEqual(models["text-embedding-3-small"].status, "unavailable")
        self.assertTrue(models["gpt-4o-audio-preview"].supports_audio_input)

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, b"not json")):
            report = self.provider.discover_models("sk-openai-test")
        self.assertEqual(report.status, "failed")
        self.assertEqual(report.error.category, "invalid_response")

        error_payload = {"error": {"message": "invalid api key sk-openai-secret", "type": "invalid_api_key"}}
        error = HTTPError(
            "https://api.openai.com/v1/models",
            401,
            "error",
            hdrs=None,
            fp=BytesIO(json.dumps(error_payload).encode("utf-8")),
        )
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=error):
            report = self.provider.discover_models("sk-openai-test")
        self.assertEqual(report.status, "failed")
        self.assertEqual(report.error.category, "authentication_error")
        self.assertNotIn("sk-openai-secret", report.error.safe_message)


class AnthropicProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = AnthropicProvider()

    def test_execute_uses_expected_http_contract(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            payload = {
                "model": "claude-3-5-sonnet",
                "content": [{"text": '{"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"}'}],
                "usage": {"input_tokens": 10, "output_tokens": 6, "cache_read_input_tokens": 3},
                "stop_reason": "end_turn",
            }
            return FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake_urlopen):
            response = self.provider.execute(_request(), api_key="sk-anthropic-test", model_id="claude-3-5-sonnet", prompt_text='{"status":"ok"}')

        req = captured["request"]
        headers = dict(req.header_items())
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(headers["X-api-key"], "sk-anthropic-test")
        self.assertEqual(headers["Anthropic-version"], self.provider.api_version)
        self.assertEqual(captured["timeout"], 30.0)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["model"], "claude-3-5-sonnet")
        self.assertEqual(body["max_tokens"], 128)
        self.assertEqual(body["messages"][0]["role"], "user")
        self.assertEqual(response.usage.input_tokens, 10)
        self.assertEqual(response.usage.cached_input_tokens, 3)

    def test_test_credentials_uses_expected_http_contract(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeHTTPResponse(200, b'{"data":[{"id":"model-1"}]}')

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake_urlopen):
            diagnostic = self.provider.test_credentials("sk-anthropic-test")

        req = captured["request"]
        headers = dict(req.header_items())
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, "https://api.anthropic.com/v1/models")
        self.assertEqual(headers["X-api-key"], "sk-anthropic-test")
        self.assertEqual(headers["Anthropic-version"], self.provider.api_version)
        self.assertEqual(captured["timeout"], 20.0)
        self.assertEqual(diagnostic.status, "ok")

    def test_error_mapping_and_sanitization(self) -> None:
        cases = [
            (401, {"error": {"message": "invalid api key sk-anthropic-secret", "type": "invalid_api_key"}}, "authentication_error"),
            (403, {"error": {"message": "insufficient credit", "type": "billing"}}, "billing_error"),
            (429, {"error": {"message": "rate limit exceeded", "type": "rate_limit"}}, "rate_limit_error"),
            (404, {"error": {"message": "model does not exist", "type": "model_not_found"}}, "model_unavailable"),
        ]
        for status, payload, expected_category in cases:
            with self.subTest(status=status):
                error = HTTPError(
                    "https://api.anthropic.com/v1/messages",
                    status,
                    "error",
                    hdrs=None,
                    fp=BytesIO(json.dumps(payload).encode("utf-8")),
                )

                def fake_urlopen(request, timeout):
                    raise error

                with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake_urlopen):
                    response = self.provider.execute(_request(), api_key="sk-anthropic-test", model_id="missing-model", prompt_text='{"status":"ok"}')

                self.assertIsNotNone(response.error)
                self.assertEqual(response.error.category, expected_category)
                self.assertNotIn("sk-anthropic-secret", response.error.safe_message)

    def test_network_timeout_and_malformed_responses(self) -> None:
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=TimeoutError("socket timeout sk-anthropic-secret")):
            response = self.provider.execute(_request(), api_key="sk-anthropic-test", model_id="claude-3-5-sonnet", prompt_text='{"status":"ok"}')
        self.assertEqual(response.error.category, "timeout")
        self.assertNotIn("sk-anthropic-secret", response.error.safe_message)

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, b"not json")):
            diagnostic = self.provider.test_credentials("sk-anthropic-test")
        self.assertEqual(diagnostic.status, "failed")
        self.assertEqual(diagnostic.error["category"], "invalid_response")

        payload = {
            "model": "claude-3-5-sonnet",
            "content": [{"text": '{"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"}'}],
        }
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            response = self.provider.execute(_request(), api_key="sk-anthropic-test", model_id="claude-3-5-sonnet", prompt_text='{"status":"ok"}')
        self.assertIsNone(response.error)
        self.assertEqual(response.usage.input_tokens, 0)
        self.assertEqual(response.usage.output_tokens, 0)

    def test_discover_models_normalizes_catalog_and_reports_errors(self) -> None:
        payload = {
            "data": [
                {"id": "claude-3-5-sonnet-latest", "display_name": "Claude 3.5 Sonnet"},
                {"id": "claude-3-5-sonnet-latest", "display_name": "Claude 3.5 Sonnet duplicate"},
                {"id": "haiku-search", "display_name": "Haiku Search"},
            ]
        }
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", return_value=FakeHTTPResponse(200, json.dumps(payload).encode("utf-8"))):
            report = self.provider.discover_models("sk-anthropic-test")
        self.assertEqual(report.status, "ok")
        self.assertEqual(report.found_count, 2)
        self.assertEqual(report.compatible_count, 1)
        models = {model.model_id: model for model in report.models}
        self.assertEqual(models["haiku-search"].status, "unavailable")

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=TimeoutError("socket timeout sk-anthropic-secret")):
            report = self.provider.discover_models("sk-anthropic-test")
        self.assertEqual(report.status, "failed")
        self.assertEqual(report.error.category, "timeout")
        self.assertNotIn("sk-anthropic-secret", report.error.safe_message)


if __name__ == "__main__":
    unittest.main()
