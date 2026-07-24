"""Tests for per-model OpenRouter provider preferences."""

import tempfile
import unittest
from pathlib import Path

from src.generator import load_provider_order

CONFIG = """
models:
  fast-model:
    providers:
      openrouter:
        openrouter_id: org/fast-model
        model: openrouter/org/fast-model
        provider_order: [cerebras, groq]
  auto-model:
    providers:
      openrouter:
        openrouter_id: org/auto-model
        model: openrouter/org/auto-model
"""


class ProviderOrderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp.name) / "models.yaml"
        self.config_path.write_text(CONFIG, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_order_for_pinned_model(self):
        order = load_provider_order("openrouter/org/fast-model", self.config_path)
        self.assertEqual(order, ["cerebras", "groq"])

    def test_returns_none_without_order(self):
        self.assertIsNone(
            load_provider_order("openrouter/org/auto-model", self.config_path)
        )

    def test_returns_none_for_unknown_model(self):
        self.assertIsNone(
            load_provider_order("openrouter/org/other", self.config_path)
        )

    def test_returns_none_when_config_missing(self):
        self.assertIsNone(
            load_provider_order(
                "openrouter/org/fast-model",
                Path(self.tmp.name) / "nope.yaml",
            )
        )

    def test_real_config_pins_gpt_oss_to_cerebras(self):
        order = load_provider_order("openrouter/openai/gpt-oss-120b")
        self.assertEqual(order[0], "cerebras")


if __name__ == "__main__":
    unittest.main()
