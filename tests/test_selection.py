import unittest

from src.selection import (
    ScoredSolution,
    generate_candidate_pairs,
    select_best_candidate,
    select_best_pair,
)


def scores(intent, correctness, scope, quality):
    return {
        "intent": intent,
        "correctness": correctness,
        "scope": scope,
        "quality": quality,
    }


def solution(solution_id, scores, objective_metrics=None):
    return ScoredSolution(
        solution_id=solution_id,
        scores=scores,
        objective_metrics=objective_metrics or {},
    )


class SelectionTest(unittest.TestCase):
    def test_generates_all_candidate_pairs_with_metrics(self):
        candidates = generate_candidate_pairs(
            [
                solution("a", scores(5, 1, 5, 1)),
                solution("b", scores(1, 5, 1, 5)),
                solution("c", scores(3, 3, 3, 3)),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=4,
        )

        self.assertEqual(len(candidates), 3)
        ab = next(c for c in candidates if c.solution_ids == ("a", "b"))
        self.assertEqual(ab.subjective_average, 3.0)
        self.assertEqual(ab.subjective_average_gap, 0.0)
        self.assertEqual(ab.subscore_diversity, 16.0)
        self.assertTrue(ab.feasible)

    def test_marks_candidates_infeasible_without_dropping_them(self):
        candidates = generate_candidate_pairs(
            [
                solution("a", scores(5, 5, 5, 5)),
                solution("b", scores(1, 1, 1, 1)),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=0.0,
        )

        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].feasible)

    def test_uses_subjective_average_when_profiles_are_equally_different(self):
        best = select_best_pair(
            [
                solution("a", scores(5, 5, 5, 5)),
                solution("b", scores(1, 1, 1, 1)),
                solution("c", scores(4, 4, 4, 4)),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=0.0,
        )

        self.assertEqual(best.solution_ids, ("a", "c"))
        self.assertEqual(best.subjective_average_gap, 1.0)
        self.assertFalse(best.feasible)

    def test_selects_best_from_generated_candidates(self):
        candidates = generate_candidate_pairs(
            [
                solution("a", scores(5, 1, 5, 1)),
                solution("b", scores(1, 5, 1, 5)),
                solution("c", scores(5, 5, 5, 5)),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=0.0,
        )

        best = select_best_candidate(candidates)

        self.assertEqual(best.solution_ids, ("a", "b"))

    def test_select_best_candidate_requires_candidates(self):
        with self.assertRaises(ValueError):
            select_best_candidate([])

    def test_prioritizes_different_subjective_profile_within_average_gap(self):
        best = select_best_pair(
            [
                solution("a", scores(5, 1, 5, 1)),
                solution("b", scores(1, 5, 1, 5)),
                solution("c", scores(5, 5, 5, 5)),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=0.0,
        )

        self.assertEqual(best.solution_ids, ("a", "b"))
        self.assertEqual(best.subjective_average_gap, 0.0)

    def test_ignores_profile_difference_when_average_gap_is_too_large(self):
        best = select_best_pair(
            [
                solution("a", scores(1, 1, 5, 4)),
                solution("b", scores(5, 5, 2, 4)),
                solution("c", scores(5, 5, 5, 2)),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=0.0,
        )

        self.assertEqual(best.solution_ids, ("b", "c"))
        self.assertEqual(best.subjective_average_gap, 0.25)

    def test_tie_prefers_different_objective_values(self):
        best = select_best_pair(
            [
                solution(
                    "a",
                    scores(3, 3, 3, 3),
                    {"completion_time_seconds": 10, "step_count": 1},
                ),
                solution(
                    "b",
                    scores(3, 3, 3, 3),
                    {"completion_time_seconds": 11, "step_count": 1},
                ),
                solution(
                    "c",
                    scores(3, 3, 3, 3),
                    {"completion_time_seconds": 30, "step_count": 8},
                ),
            ],
            max_average_gap=0.75,
            min_subscore_diversity=0.0,
        )

        self.assertEqual(best.solution_ids, ("a", "c"))

    def test_requires_two_solutions(self):
        with self.assertRaises(ValueError):
            select_best_pair(
                [
                    solution(
                        "a",
                        scores(3, 3, 3, 3),
                    )
                ],
                max_average_gap=0.75,
                min_subscore_diversity=0.0,
            )

    def test_requires_all_subjective_scores(self):
        with self.assertRaises(ValueError):
            select_best_pair(
                [
                    solution("a", {"intent": 3, "correctness": 3}),
                    solution(
                        "b",
                        scores(3, 3, 3, 3),
                    ),
                ],
                max_average_gap=0.75,
                min_subscore_diversity=0.0,
            )


if __name__ == "__main__":
    unittest.main()
