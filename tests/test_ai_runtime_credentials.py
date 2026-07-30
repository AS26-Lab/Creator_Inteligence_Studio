from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.ai_runtime.credentials import (
    CredentialStore,
    DevelopmentEnvironmentCredentialBackend,
    InMemoryCredentialBackend,
    WindowsCredentialManagerBackend,
)


class CredentialStoreTests(unittest.TestCase):
    def test_reference_is_stable_and_creator_safe(self) -> None:
        reference = CredentialStore.reference_for_provider("openai")
        self.assertEqual(reference, "ai.openai.api_key")
        self.assertNotIn("creator", reference)
        self.assertNotIn("Authorization", reference)

    def test_memory_backend_round_trip_and_delete(self) -> None:
        store = CredentialStore.build_memory()
        reference = CredentialStore.reference_for_provider("anthropic")
        store.save(reference, "sk-anthropic-test")
        self.assertIsInstance(store.backend, InMemoryCredentialBackend)
        self.assertEqual(store.load(reference), "sk-anthropic-test")
        self.assertTrue(store.mask("sk-anthropic-test").endswith("test"))
        self.assertNotEqual(store.mask("sk-anthropic-test"), "sk-anthropic-test")
        store.delete(reference)
        self.assertIsNone(store.load(reference))

    def test_mask_never_returns_full_secret(self) -> None:
        store = CredentialStore.build_memory()
        self.assertEqual(store.mask(""), "no configurado")
        self.assertEqual(store.mask("abc"), "****abc")
        self.assertNotEqual(store.mask("sk-test"), "sk-test")

    def test_environment_backend_is_explicit_only(self) -> None:
        with patch.dict(os.environ, {"CIS_ENABLE_ENV_CREDENTIALS": "1"}, clear=False):
            store = CredentialStore.build_default()
            self.assertIsInstance(store.backend, DevelopmentEnvironmentCredentialBackend)
            reference = CredentialStore.reference_for_provider("openai")
            store.save(reference, "sk-env-test")
            self.assertEqual(store.load(reference), "sk-env-test")
            store.delete(reference)
            self.assertIsNone(store.load(reference))

    def test_windows_backend_is_selected_when_available(self) -> None:
        with patch.dict(os.environ, {"CIS_ENABLE_ENV_CREDENTIALS": "0"}, clear=False), patch.object(
            WindowsCredentialManagerBackend,
            "is_available",
            return_value=True,
        ):
            store = CredentialStore.build_default()
            self.assertIsInstance(store.backend, WindowsCredentialManagerBackend)

    def test_windows_backend_target_prefix_is_stable(self) -> None:
        backend = WindowsCredentialManagerBackend(target_prefix="CreatorIntelligenceStudio")
        self.assertEqual(backend._target("ai.openai.api_key"), "CreatorIntelligenceStudio:ai.openai.api_key")


if __name__ == "__main__":
    unittest.main()
