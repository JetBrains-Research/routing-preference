import json
import tempfile
import unittest
from pathlib import Path

from src.selection.config import (
    load_selection_config,
    selection_config_from_dict,
)


class SelectionConfigTest(unittest.TestCase):
    def test_requires_config_file(self):
        with self.assertRaises(FileNotFoundError):
            load_selection_config(Path("missing-selection-config.json"))

    def test_loads_default_config_file(self):
        config = load_selection_config()

        self.assertEqual(config.quality_bands["bad"], (1.0, 2.5))
        self.assertEqual(config.quality_bands["medium"], (2.5, 3.75))
        self.assertEqual(config.quality_bands["good"], (3.75, 5.0))

    def test_loads_config_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "selection.json"
            path.write_text(
                json.dumps(
                    {
                        "max_average_gap": 0.5,
                        "min_subscore_diversity": 3,
                        "local_pair_quality_weight": 2,
                        "model_coverage_weight": 0.7,
                        "quality_bands": {
                            "low": [1, 2],
                            "high": [2, 5],
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = load_selection_config(path)

        self.assertEqual(config.max_average_gap, 0.5)
        self.assertEqual(config.min_subscore_diversity, 3.0)
        self.assertEqual(config.local_pair_quality_weight, 2.0)
        self.assertEqual(config.model_coverage_weight, 0.7)
        self.assertEqual(config.quality_bands["low"], (1.0, 2.0))

    def test_quality_bands_are_optional_without_band_balancing(self):
        config = selection_config_from_dict({"max_average_gap": 1})

        self.assertIsNone(config.quality_bands)

    def test_quality_bands_required_when_band_balancing_enabled(self):
        with self.assertRaises(ValueError):
            selection_config_from_dict(
                {
                    "quality_band_balance_weight": 1,
                }
            )

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            selection_config_from_dict({"max_average_gap": -1})

        with self.assertRaises(ValueError):
            selection_config_from_dict({"quality_bands": {"bad": [3, 2]}})


if __name__ == "__main__":
    unittest.main()
