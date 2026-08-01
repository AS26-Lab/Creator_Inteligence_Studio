from __future__ import annotations

import unittest

from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


def _make_model(
    model_id: str,
    display_name: str,
    *,
    status: str = "testing",
    snapshot_or_version: str | None = None,
    supports_structured_output: bool = True,
    supports_image_input: bool = False,
    supports_audio_input: bool = False,
    input_price_per_million: float | None = None,
    output_price_per_million: float | None = None,
    capabilities_json: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "model_id": model_id,
        "display_name": display_name,
        "snapshot_or_version": snapshot_or_version,
        "status": status,
        "supports_structured_output": supports_structured_output,
        "supports_image_input": supports_image_input,
        "supports_audio_input": supports_audio_input,
        "input_price_per_million": input_price_per_million,
        "output_price_per_million": output_price_per_million,
    }
    if capabilities_json is not None:
        payload["capabilities_json"] = capabilities_json
    return payload


def build_role_catalog() -> list[dict[str, object]]:
    models: list[dict[str, object]] = [
        _make_model("gpt-4.1-mini", "GPT-4.1 mini", status="approved", input_price_per_million=0.15, output_price_per_million=0.6),
        _make_model("gpt-4.1", "GPT-4.1", status="approved", input_price_per_million=1.5, output_price_per_million=6.0),
        _make_model("gpt-4o-mini", "GPT-4o mini", status="approved", input_price_per_million=0.1, output_price_per_million=0.4, supports_image_input=True),
        _make_model("gpt-3.5-turbo", "GPT-3.5 Turbo", status="deprecated", input_price_per_million=0.5, output_price_per_million=1.5),
        _make_model("claude-4-sonnet", "Claude 4 Sonnet", status="approved", input_price_per_million=3.0, output_price_per_million=15.0),
        _make_model("claude-3-5-sonnet", "Claude 3.5 Sonnet", status="approved", input_price_per_million=3.0, output_price_per_million=15.0),
    ]
    for index in range(7):
        models.append(
            _make_model(
                f"compatible-chat-{index}",
                f"Compatible Chat {index}",
                status="testing",
                input_price_per_million=None,
                output_price_per_million=None,
            )
        )
    for index in range(8):
        models.append(
            _make_model(
                f"snapshot-chat-{index}-2026-07-01",
                f"Snapshot Chat {index}",
                status="testing",
                snapshot_or_version="2026-07-01",
                input_price_per_million=0.2,
                output_price_per_million=0.8,
            )
        )
    technical_prefixes = [
        "audio",
        "tts",
        "search",
        "codex",
        "embedding",
        "moderation",
        "realtime",
        "legacy",
    ]
    counter = 0
    while len(models) < 115:
        prefix = technical_prefixes[counter % len(technical_prefixes)]
        models.append(
            _make_model(
                f"{prefix}-model-{counter}",
                f"{prefix.title()} Model {counter}",
                status="approved" if prefix == "legacy" else "testing",
                supports_structured_output=prefix not in {"audio", "tts", "embedding"},
                supports_image_input=False,
                supports_audio_input=prefix in {"audio", "tts"},
                capabilities_json={"specialization": prefix},
            )
        )
        counter += 1
    return models


class AIRuntimeModelSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture(provider="anthropic")
        self.addCleanup(self.fixture.cleanup)
        self.catalog = build_role_catalog()
        self.fixture.service.providers["openai"] = FakeProvider("openai", discovered_models=self.catalog)
        self.fixture.service.refresh_provider_models("openai")

    def test_default_cheap_structured_selector_is_short_and_relevant(self) -> None:
        summary = self.fixture.service.list_model_selection("openai", "cheap_structured_model")
        self.assertEqual(summary["catalog_count"], 115)
        self.assertEqual(summary["recommended_count"], 5)
        self.assertEqual(summary["compatible_count"], 12)
        self.assertLessEqual(summary["visible_count"], 12)
        ids = [row["model_id"] for row in summary["items"] if row["is_visible"]]
        self.assertTrue(all("audio" not in model_id for model_id in ids))
        self.assertTrue(all("tts" not in model_id for model_id in ids))
        self.assertTrue(all("search" not in model_id for model_id in ids))
        self.assertTrue(all("codex" not in model_id for model_id in ids))
        self.assertTrue(all("embed" not in model_id for model_id in ids))
        self.assertTrue(all("moderation" not in model_id for model_id in ids))
        self.assertTrue(all("preview" not in model_id for model_id in ids))

    def test_show_all_reveals_full_catalog_and_search_filters(self) -> None:
        summary = self.fixture.service.list_model_selection(
            "openai",
            "cheap_structured_model",
            show_non_recommended=True,
            show_all_models=True,
            show_snapshots_and_previews=True,
        )
        self.assertEqual(summary["visible_count"], 115)
        search_summary = self.fixture.service.list_model_selection(
            "openai",
            "cheap_structured_model",
            query="gpt-4.1-mini",
            show_non_recommended=True,
            show_all_models=True,
            show_snapshots_and_previews=True,
        )
        visible_ids = [row["model_id"] for row in search_summary["items"] if row["is_visible"]]
        self.assertEqual(visible_ids, ["gpt-4.1-mini"])

    def test_snapshots_and_previews_are_hidden_by_default(self) -> None:
        summary = self.fixture.service.list_model_selection("openai", "cheap_structured_model")
        self.assertFalse(any(row["is_visible"] and row["category"] == "preview" for row in summary["items"]))
        advanced = self.fixture.service.list_model_selection(
            "openai",
            "cheap_structured_model",
            show_non_recommended=True,
            show_snapshots_and_previews=True,
        )
        self.assertTrue(any(row["category"] == "advanced" for row in advanced["items"] if row["is_visible"]))

    def test_assigned_model_is_preserved_and_incompatible_models_are_not_assignable(self) -> None:
        self.fixture.service.assign_role(
            role="cheap_structured_model",
            provider="openai",
            model_id="gpt-4.1-mini",
            creator_id=None,
            display_name="GPT-4.1 mini",
            is_default=False,
            is_enabled=True,
            fallback_policy="none",
            status="testing",
            capabilities_json={"structured_output": True},
            snapshot_or_version=None,
        )
        summary = self.fixture.service.list_model_selection(
            "openai",
            "cheap_structured_model",
            selected_model_id="gpt-4.1-mini",
        )
        self.assertTrue(any(row["model_id"] == "gpt-4.1-mini" for row in summary["items"] if row["is_visible"]))
        with self.assertRaises(ValueError):
            self.fixture.service.assign_role(
                role="cheap_structured_model",
                provider="openai",
                model_id="audio-model-0",
                creator_id=None,
                display_name="Audio Model 0",
                is_default=False,
                is_enabled=True,
                fallback_policy="none",
                status="testing",
                capabilities_json={"audio_input": True},
                snapshot_or_version=None,
            )

    def test_preview_and_legacy_models_do_not_win_by_sort_order(self) -> None:
        summary = self.fixture.service.list_model_selection(
            "openai",
            "cheap_structured_model",
            show_non_recommended=True,
            show_all_models=True,
            show_snapshots_and_previews=True,
        )
        visible = [row for row in summary["items"] if row["is_visible"]]
        self.assertGreater(len(visible), 0)
        self.assertNotEqual(visible[0]["model_id"], "gpt-3.5-turbo")


if __name__ == "__main__":
    unittest.main()
