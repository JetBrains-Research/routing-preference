import unittest

from src.selection import (
    ScoredSolution,
    SelectionConfig,
    generate_candidate_pairs,
    select_balanced_pairs,
)


def scores(intent, correctness, scope, quality):
    return {
        "intent": intent,
        "correctness": correctness,
        "scope": scope,
        "quality": quality,
    }


def solution(solution_id, model_slug, score_values):
    return ScoredSolution(
        solution_id=solution_id,
        model_slug=model_slug,
        run_id="run",
        relative_path=f"issue/{model_slug}/run",
        scores=scores(*score_values),
    )


def candidates(*solutions, max_average_gap=4.0, min_subscore_diversity=0.0):
    return generate_candidate_pairs(
        list(solutions),
        max_average_gap=max_average_gap,
        min_subscore_diversity=min_subscore_diversity,
    )


class BalancedSelectionTest(unittest.TestCase):
    def test_selects_one_pair_per_issue_and_tracks_model_usage(self):
        config = SelectionConfig(
            model_coverage_weight=0.0,
            model_balance_weight=0.0,
            quality_bands={"all": (1.0, 5.0)},
        )
        result = select_balanced_pairs(
            {
                "issue-1": candidates(
                    solution("a1", "model-a", (5, 1, 5, 1)),
                    solution("b1", "model-b", (1, 5, 1, 5)),
                ),
                "issue-2": candidates(
                    solution("a2", "model-a", (3, 3, 3, 3)),
                    solution("c2", "model-c", (3, 3, 3, 3)),
                ),
            },
            config,
        )

        self.assertEqual(set(result.selections), {"issue-1", "issue-2"})
        self.assertEqual(result.model_usage["model-a"], 2)
        self.assertEqual(result.model_usage["model-b"], 1)
        self.assertEqual(result.model_usage["model-c"], 1)

    def test_prefers_underrepresented_models_when_configured(self):
        config = SelectionConfig(
            local_pair_quality_weight=1.0,
            model_coverage_weight=5.0,
            model_balance_weight=1.0,
            quality_bands={"all": (1.0, 5.0)},
        )
        issue_candidates = {
            "issue-1": candidates(
                solution("a1", "model-a", (5, 1, 5, 1)),
                solution("b1", "model-b", (1, 5, 1, 5)),
            ),
            "issue-2": candidates(
                solution("a2", "model-a", (5, 1, 5, 1)),
                solution("b2", "model-b", (1, 5, 1, 5)),
                solution("c2", "model-c", (3, 3, 3, 3)),
            ),
        }

        result = select_balanced_pairs(issue_candidates, config)
        selected_issue_2 = result.selections["issue-2"].selected[0].candidate

        self.assertIn("model-c", result.model_usage)
        self.assertIn(
            "model-c",
            {
                selected_issue_2.solution_a.model_slug,
                selected_issue_2.solution_b.model_slug,
            },
        )
        self.assertEqual(result.model_usage["model-c"], 1)

    def test_selects_multiple_distinct_pairs_per_issue(self):
        config = SelectionConfig(quality_bands={"all": (1.0, 5.0)})
        result = select_balanced_pairs(
            {
                "issue-1": candidates(
                    solution("a1", "model-a", (5, 1, 5, 1)),
                    solution("b1", "model-b", (1, 5, 1, 5)),
                    solution("c1", "model-c", (3, 3, 3, 3)),
                ),
            },
            config,
            pairs_per_issue=2,
        )

        picked = result.selections["issue-1"].selected
        self.assertEqual(len(picked), 2)
        ids = [tuple(p.candidate.solution_ids) for p in picked]
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual(sum(result.model_usage.values()), 4)

    def test_rejects_more_pairs_than_candidates(self):
        config = SelectionConfig(quality_bands={"all": (1.0, 5.0)})
        with self.assertRaises(ValueError):
            select_balanced_pairs(
                {
                    "issue-1": candidates(
                        solution("a1", "model-a", (5, 1, 5, 1)),
                        solution("b1", "model-b", (1, 5, 1, 5)),
                    ),
                },
                config,
                pairs_per_issue=2,
            )

    def test_uses_fallback_when_no_candidate_is_feasible(self):
        config = SelectionConfig(
            max_average_gap=0.0,
            min_subscore_diversity=100.0,
            quality_bands={"all": (1.0, 5.0)},
        )
        result = select_balanced_pairs(
            {
                "issue-1": candidates(
                    solution("a1", "model-a", (5, 5, 5, 5)),
                    solution("b1", "model-b", (1, 1, 1, 1)),
                    max_average_gap=0.0,
                    min_subscore_diversity=100.0,
                ),
            },
            config,
        )

        self.assertTrue(result.selections["issue-1"].used_fallback)


if __name__ == "__main__":
    unittest.main()
