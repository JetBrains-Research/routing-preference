import importlib.util
import unittest

from scripts.demo_synthetic_selection import MODELS, SYNTHETIC_ISSUES, _solution
from src.selection import (
    SelectionConfig,
    generate_candidate_pairs,
    select_balanced_pairs,
    select_balanced_pairs_cpsat,
)


def synthetic_candidates(max_average_gap=0.75, min_subscore_diversity=4.0):
    return {
        issue_id: generate_candidate_pairs(
            [
                _solution(issue_id, model, scores)
                for model, scores in zip(MODELS, score_rows)
            ],
            max_average_gap=max_average_gap,
            min_subscore_diversity=min_subscore_diversity,
        )
        for issue_id, score_rows in SYNTHETIC_ISSUES.items()
    }


def synthetic_config(**overrides):
    values = {
        "max_average_gap": 0.75,
        "min_subscore_diversity": 4.0,
        "local_pair_quality_weight": 1.0,
        "model_coverage_weight": 2.0,
        "model_balance_weight": 1.0,
        "quality_bands": {
            "bad": (1.0, 2.5),
            "medium": (2.5, 3.75),
            "good": (3.75, 5.0),
        },
    }
    values.update(overrides)
    return SelectionConfig(**values)


class SyntheticSelectionTest(unittest.TestCase):
    def test_synthetic_vectors_have_feasible_candidates_per_issue(self):
        issue_candidates = synthetic_candidates()

        self.assertEqual(set(issue_candidates), set(SYNTHETIC_ISSUES))
        for candidates in issue_candidates.values():
            self.assertEqual(len(candidates), 21)
            self.assertTrue(any(candidate.feasible for candidate in candidates))

    def test_greedy_balanced_selection_uses_multiple_quality_bands(self):
        result = select_balanced_pairs(
            synthetic_candidates(),
            synthetic_config(),
        )

        self.assertEqual(set(result.selections), set(SYNTHETIC_ISSUES))
        self.assertGreaterEqual(len(result.quality_band_usage), 3)
        self.assertGreaterEqual(len(result.model_usage), 4)

    @unittest.skipIf(
        importlib.util.find_spec("ortools") is None,
        "OR-Tools is not installed",
    )
    def test_cpsat_balances_model_usage_on_synthetic_vectors(self):
        result = select_balanced_pairs_cpsat(
            synthetic_candidates(),
            synthetic_config(
                local_pair_quality_weight=0.0,
                model_coverage_weight=0.0,
                model_balance_weight=1.0,
            ),
        )

        usage_values = list(result.model_usage.values())
        self.assertEqual(set(result.selections), set(SYNTHETIC_ISSUES))
        self.assertLessEqual(max(usage_values) - min(usage_values), 1)


if __name__ == "__main__":
    unittest.main()
