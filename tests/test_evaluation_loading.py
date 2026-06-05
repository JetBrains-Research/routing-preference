import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation import (
    build_scoring_evaluation_rows,
    default_characteristics,
    load_scoring_evaluation,
    resolve_scoring_runs,
    write_scoring_characteristic_comparison_csvs,
)

CHARACTERISTICS = ("intent", "correctness", "scope", "quality")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def score_file(
    *,
    issue_id: str = "issue-1",
    solution_id: str = "model-a__run-1",
    judge_model: str = "openai/gpt-5.2",
    scores: dict[str, int] | None = None,
    granularity: str = "all",
    characteristic_id: str | None = None,
) -> dict:
    scores = scores or {char: 5 for char in CHARACTERISTICS}
    return {
        "solution_folder": solution_id,
        "issue_id": issue_id,
        "solution_model": "model/a",
        "judge_model": judge_model,
        "scores": [
            {"characteristic_id": char, "value": value, "reasoning": ""}
            for char, value in scores.items()
        ],
        "overall_score": sum(scores.values()) / len(scores),
        "created_at": "now",
        "exposure": "V1",
        "basis": "scoring",
        "granularity": granularity,
        "characteristic_id": characteristic_id,
        "score_scale": [1, 5],
        "empty_solution": False,
    }


class EvaluationLoadingTest(unittest.TestCase):
    def test_loads_manual_all_and_single_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions = root / "solutions"
            judgments = root / "judgments"
            run = solutions / "issue-1" / "model-a" / "run-1"
            write_json(run / "solution.json", {"issue_id": "issue-1"})

            solution_id = "model-a__run-1"
            write_json(
                judgments / "issue-1" / "scoring" / "manual" / f"{solution_id}.json",
                score_file(
                    solution_id=solution_id,
                    judge_model="manual",
                    scores={"intent": 5, "correctness": 4, "scope": 3, "quality": 2},
                )
                | {"empty_solution": False},
            )
            write_json(
                judgments
                / "issue-1"
                / "scoring"
                / "openai_gpt-5.2__V1_all"
                / f"{solution_id}.json",
                score_file(solution_id=solution_id),
            )
            write_json(
                judgments
                / "issue-1"
                / "scoring"
                / "openai_gpt-5.2__V1_single"
                / f"{solution_id}.json",
                score_file(
                    solution_id=solution_id,
                    scores={char: 4 for char in CHARACTERISTICS},
                    granularity="single",
                ),
            )

            loaded = load_scoring_evaluation(
                solutions_dir=solutions,
                judgments_dir=judgments,
                judge_folders=[
                    "openai_gpt-5.2__V1_all",
                    "openai_gpt-5.2__V1_single",
                ],
            )

            self.assertEqual(len(loaded.solutions), 1)
            solution = loaded.solutions[0]
            self.assertEqual(solution.solution_model, "model/a")
            self.assertFalse(solution.empty_solution)
            self.assertEqual(solution.manual.scores["correctness"], 4)
            single = solution.judge_scores["openai_gpt-5.2__V1_single"]
            self.assertEqual(single.overall_score, 4.0)
            self.assertEqual(single.path.name, f"{solution_id}.json")

    def test_rejects_missing_manual_issue_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions = root / "solutions"
            judgments = root / "judgments"
            run = solutions / "issue-1" / "model-a" / "run-1"
            write_json(run / "solution.json", {"issue_id": "issue-1"})

            with self.assertRaisesRegex(ValueError, "Manual scoring folder"):
                load_scoring_evaluation(
                    solutions_dir=solutions,
                    judgments_dir=judgments,
                    judge_folders=["openai_gpt-5.2__V1_all"],
                )

    def test_rejects_legacy_single_characteristic_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            judgments = root / "judgments"
            (judgments / "issue-1" / "scoring" / "openai_gpt-5.2__V1_intent").mkdir(
                parents=True
            )

            with self.assertRaisesRegex(ValueError, "Legacy per-characteristic"):
                resolve_scoring_runs(
                    judgments_dir=judgments,
                    judge_folders=["openai_gpt-5.2__V1_intent"],
                )

    def test_builds_scoring_evaluation_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions = root / "solutions"
            judgments = root / "judgments"
            output = root / "evaluation_run"
            run = solutions / "issue-1" / "model-a" / "run-1"
            write_json(run / "solution.json", {"issue_id": "issue-1"})

            solution_id = "model-a__run-1"
            write_json(
                judgments / "issue-1" / "scoring" / "manual" / f"{solution_id}.json",
                score_file(
                    solution_id=solution_id,
                    judge_model="manual",
                    scores={"intent": 5, "correctness": 4, "scope": 3, "quality": 2},
                )
                | {"empty_solution": False},
            )
            write_json(
                judgments
                / "issue-1"
                / "scoring"
                / "openai_gpt-5.2__V1_single"
                / f"{solution_id}.json",
                score_file(
                    solution_id=solution_id,
                    scores={"intent": 4, "correctness": 4, "scope": 2, "quality": 1},
                    granularity="single",
                ),
            )

            rows, result = build_scoring_evaluation_rows(
                solutions_dir=solutions,
                judgments_dir=judgments,
                judge_folders=[],
                output_path=output,
            )

            self.assertEqual(len(rows), 4)
            self.assertEqual(result.row_count, 4)
            self.assertEqual(result.solution_count, 1)
            self.assertEqual(result.issue_count, 1)
            intent = next(row for row in rows if row["characteristic"] == "intent")
            self.assertEqual(intent["judge_run_id"], "openai_gpt-5.2__V1_single")
            self.assertEqual(intent["exposure"], "V1")
            self.assertEqual(intent["granularity"], "single")
            self.assertEqual(intent["manual_score"], 5)
            self.assertEqual(intent["judge_score"], 4)
            self.assertEqual(intent["signed_error"], -1)
            self.assertEqual(intent["absolute_error"], 1)

    def test_rejects_issue_without_manual_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions = root / "solutions"
            judgments = root / "judgments"

            run_one = solutions / "issue-1" / "model-a" / "run-1"
            run_two = solutions / "issue-2" / "model-b" / "run-1"
            write_json(run_one / "solution.json", {"issue_id": "issue-1"})
            write_json(run_two / "solution.json", {"issue_id": "issue-2"})

            solution_id = "model-a__run-1"
            write_json(
                judgments / "issue-1" / "scoring" / "manual" / f"{solution_id}.json",
                score_file(solution_id=solution_id, judge_model="manual")
                | {"empty_solution": False},
            )
            write_json(
                judgments
                / "issue-1"
                / "scoring"
                / "openai_gpt-5.2__V1_all"
                / f"{solution_id}.json",
                score_file(solution_id=solution_id),
            )

            with self.assertRaisesRegex(ValueError, "Manual scoring folder"):
                build_scoring_evaluation_rows(
                    solutions_dir=solutions,
                    judgments_dir=judgments,
                    judge_folders=[],
                    output_path=root / "evaluation_run",
                )

    def test_rejects_solution_without_manual_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions = root / "solutions"
            judgments = root / "judgments"

            run_one = solutions / "issue-1" / "model-a" / "run-1"
            run_two = solutions / "issue-1" / "model-b" / "run-1"
            write_json(run_one / "solution.json", {"issue_id": "issue-1"})
            write_json(run_two / "solution.json", {"issue_id": "issue-1"})

            solution_id = "model-a__run-1"
            write_json(
                judgments / "issue-1" / "scoring" / "manual" / f"{solution_id}.json",
                score_file(solution_id=solution_id, judge_model="manual")
                | {"empty_solution": False},
            )
            write_json(
                judgments
                / "issue-1"
                / "scoring"
                / "openai_gpt-5.2__V1_all"
                / f"{solution_id}.json",
                score_file(solution_id=solution_id),
            )

            with self.assertRaisesRegex(ValueError, "Manual scoring file"):
                build_scoring_evaluation_rows(
                    solutions_dir=solutions,
                    judgments_dir=judgments,
                    judge_folders=[],
                    output_path=root / "evaluation_run",
                )

    def test_writes_characteristic_comparison_csvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "evaluation_run"
            rows = [
                {
                    "issue_id": "issue-1",
                    "solution_id": "model-a__run-1",
                    "solution_model": "model/a",
                    "empty_solution": False,
                    "judge_run_id": "openai_gpt-5.2__V1_all",
                    "judge_slug": "openai_gpt-5.2",
                    "exposure": "V1",
                    "granularity": "all",
                    "characteristic": "intent",
                    "manual_score": 5,
                    "judge_score": 4,
                    "signed_error": -1,
                    "absolute_error": 1,
                    "manual_path": "manual.json",
                    "judge_path": "judge.json",
                },
                {
                    "issue_id": "issue-2",
                    "solution_id": "model-b__run-1",
                    "solution_model": "model/b",
                    "empty_solution": False,
                    "judge_run_id": "openai_gpt-5.2__V1_all",
                    "judge_slug": "openai_gpt-5.2",
                    "exposure": "V1",
                    "granularity": "all",
                    "characteristic": "intent",
                    "manual_score": 3,
                    "judge_score": 3,
                    "signed_error": 0,
                    "absolute_error": 0,
                    "manual_path": "manual.json",
                    "judge_path": "judge.json",
                },
                {
                    "issue_id": "issue-1",
                    "solution_id": "model-a__run-1",
                    "solution_model": "model/a",
                    "empty_solution": False,
                    "judge_run_id": "openai_gpt-5.2__V1_all",
                    "judge_slug": "openai_gpt-5.2",
                    "exposure": "V1",
                    "granularity": "all",
                    "characteristic": "quality",
                    "manual_score": 3,
                    "judge_score": 5,
                    "signed_error": 2,
                    "absolute_error": 2,
                    "manual_path": "manual.json",
                    "judge_path": "judge.json",
                },
            ]

            paths = write_scoring_characteristic_comparison_csvs(
                rows=rows,
                output_dir=output_dir,
                characteristics=default_characteristics(),
                bootstrap_samples=100,
                bootstrap_seed=1,
            )

            self.assertEqual(
                set(paths),
                {"intent", "correctness", "scope", "quality", "overall"},
            )
            with open(paths["intent"], newline="", encoding="utf-8") as f:
                intent_rows = list(csv.DictReader(f))
            with open(paths["correctness"], newline="", encoding="utf-8") as f:
                correctness_rows = list(csv.DictReader(f))

            self.assertEqual(paths["intent"].name, "intent_comparison.csv")
            self.assertEqual(paths["overall"].name, "overall_comparison.csv")
            self.assertEqual(len(intent_rows), 1)
            self.assertEqual(intent_rows[0]["judge_run_id"], "openai_gpt-5.2__V1_all")
            self.assertEqual(intent_rows[0]["n"], "2")
            self.assertEqual(intent_rows[0]["issue_count"], "2")
            self.assertEqual(float(intent_rows[0]["mean_absolute_error"]), 0.5)
            self.assertEqual(float(intent_rows[0]["closeness_percent"]), 87.5)
            self.assertIn("closeness_ci_lower", intent_rows[0])
            self.assertIn("closeness_ci_upper", intent_rows[0])
            self.assertIn("macro_f1", intent_rows[0])
            self.assertIn("mae_ci_lower", intent_rows[0])
            self.assertIn("mae_ci_upper", intent_rows[0])
            self.assertNotIn("manual_score", intent_rows[0])
            self.assertNotIn("metric", intent_rows[0])
            self.assertEqual(correctness_rows, [])


if __name__ == "__main__":
    unittest.main()
