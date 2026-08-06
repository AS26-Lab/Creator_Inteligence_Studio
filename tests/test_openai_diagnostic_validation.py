from __future__ import annotations

import unittest

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRequest
from creator_intelligence_studio.infrastructure.ai_runtime.policies import AIResultValidator
from creator_intelligence_studio.presentation.desktop.views.ai_runtime_overview_view import DiagnosticsTab


def _request(*, metadata: dict[str, object] | None = None) -> AIExecutionRequest:
    return AIExecutionRequest(
        request_id="req-openai-validation",
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
        metadata=metadata or {},
    )


class OpenAIDiagnosticValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = AIResultValidator()

    def test_textual_connectivity_responses_are_accepted_after_normalization(self) -> None:
        cases = ["OK", "OK.", " OK\n", "```text\nOK.\n```", "All good"]
        for case in cases:
            with self.subTest(case=case):
                validation = self.validator.validate(request=_request(), payload="", output_text=case, response_state="content")
                self.assertEqual(validation.status, "valid")

    def test_textual_connectivity_can_use_expected_token_metadata(self) -> None:
        validation = self.validator.validate(request=_request(metadata={"expected_text": "OK"}), payload="", output_text=" ok. ", response_state="content")
        self.assertEqual(validation.status, "valid")

    def test_empty_refusal_truncated_and_content_filter_responses_are_rejected(self) -> None:
        cases = [
            ("", "empty", "Output text is empty."),
            ("I refuse.", "refusal", "Response state is refusal."),
            ("I cannot continue.", "content_filter", "Response state is content_filter."),
            ("Truncated", "truncated", "Response was truncated."),
        ]
        for text, state, expected_issue in cases:
            with self.subTest(state=state):
                validation = self.validator.validate(request=_request(), payload="", output_text=text, response_state=state)
                self.assertEqual(validation.status, "rejected")
                self.assertIn(expected_issue, validation.issues)

    def test_structured_output_validation_remains_separate(self) -> None:
        payload = {"status": "ok", "logical_role": "cheap_structured_model", "short_message": "Provider diagnostic completed successfully."}
        validation = self.validator.validate(request=_request(), payload=payload, output_text='{"status":"ok"}', response_state="content")
        self.assertEqual(validation.status, "valid")

    def test_structured_output_missing_keys_is_rejected(self) -> None:
        payload = {"status": "ok"}
        validation = self.validator.validate(request=_request(), payload=payload, output_text='{"status":"ok"}', response_state="content")
        self.assertEqual(validation.status, "rejected")
        self.assertIn("Missing keys", " ".join(validation.issues))

    def test_gui_message_for_local_validation_failure_is_user_friendly(self) -> None:
        message = DiagnosticsTab._friendly_diagnostic_message(
            None,
            "completed_with_warnings",
            {},
            {"status": "rejected", "issues": ["Output text is empty."]},
        )
        self.assertIn("no pudo validar", message.lower())


if __name__ == "__main__":
    unittest.main()
