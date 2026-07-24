import json
import tempfile
import unittest
from pathlib import Path

from src.judge.storage import judge_run_id
from src.selection import (
    SelectionConfig,
    SelectionStorage,
    generate_candidates_for_issue,
    load_scored_solutions,
    select_balanced_pairs,
    select_pair_for_issue,
)
from src.selection.storage import selection_run_id, selection_source_run_id
from src.storage import solution_id_from_run_dir


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def create_solution(
    solutions_dir: Path,
    judgments_dir: Path,
    folder: str,
    issue_id: str,
    scores: dict,
    granularity: str = "all",
    **metrics,
):
    solution_dir = solutions_dir / folder
    solution_id = solution_id_from_run_dir(solution_dir)
    objective_metrics = metrics
    write_json(
        solution_dir / "solution.json",
        {
            "issue_id": issue_id,
            "model": folder,
            "provider": "test",
            "diff": "",
            "trajectory": {},
            "duration_ms": 1000,
            "created_at": "now",
        },
    )
    if objective_metrics:
        write_json(
            solution_dir / "info.json",
            {
                "summary": "",
                "objective_metrics": objective_metrics,
                "exposed_files": [],
                "grep_exposed_files": [],
            },
        )
    else:
        write_json(
            solution_dir / "info.json",
            {
                "summary": "",
                "objective_metrics": {},
                "exposed_files": [],
                "grep_exposed_files": [],
            },
        )
    write_json(
        judgments_dir
        / issue_id
        / "scoring"
        / judge_run_id("judge", "V1", granularity, None)
        / f"{solution_id}.json",
        {
            "solution_folder": solution_id,
            "issue_id": issue_id,
            "solution_model": folder,
            "judge_model": "judge",
            "scores": [
                {"characteristic_id": key, "value": value, "reasoning": ""}
                for key, value in scores.items()
            ],
            "overall_score": sum(scores.values()) / len(scores),
            "created_at": "now",
            "exposure": "V1",
            "basis": "scoring",
            "granularity": granularity,
            "characteristic_id": None,
            "score_scale": [1, 5],
        },
    )


class SelectionStorageTest(unittest.TestCase):
    def test_loads_scored_solutions_for_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-1/model-a/run-a",
                "issue-1",
                {"intent": 5, "correctness": 5, "scope": 5, "quality": 5},
                completion_time_seconds=10,
                step_count=1,
            )
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-2/model-b/run-b",
                "issue-2",
                {"intent": 1, "correctness": 1, "scope": 1, "quality": 1},
            )

            scored = load_scored_solutions(
                solutions_dir,
                judgments_dir,
                "issue-1",
                judge_model="judge",
                exposure="V1",
            )

            self.assertEqual([s.solution_id for s in scored], ["model-a__run-a"])
            self.assertEqual(
                scored[0].relative_path,
                "issue-1/model-a/run-a",
            )
            self.assertEqual(scored[0].objective_metrics["step_count"], 1.0)

    def test_keeps_only_latest_run_per_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-1/model-a/20260101_000000_000000",
                "issue-1",
                {"intent": 1, "correctness": 1, "scope": 1, "quality": 1},
            )
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-1/model-a/20260202_000000_000000",
                "issue-1",
                {"intent": 4, "correctness": 4, "scope": 4, "quality": 4},
            )
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-1/model-b/20260101_000000_000000",
                "issue-1",
                {"intent": 3, "correctness": 3, "scope": 3, "quality": 3},
            )

            scored = load_scored_solutions(
                solutions_dir,
                judgments_dir,
                "issue-1",
                judge_model="judge",
                exposure="V1",
            )

            self.assertEqual(
                [s.solution_id for s in scored],
                [
                    "model-a__20260202_000000_000000",
                    "model-b__20260101_000000_000000",
                ],
            )
            self.assertEqual(scored[0].scores["intent"], 4.0)

    def test_ignores_boolean_objective_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-1/model-a/run-a",
                "issue-1",
                {"intent": 5, "correctness": 5, "scope": 5, "quality": 5},
                completion_time_seconds=10,
                passed=True,
            )

            scored = load_scored_solutions(
                solutions_dir,
                judgments_dir,
                "issue-1",
                judge_model="judge",
                exposure="V1",
            )

            self.assertEqual(
                scored[0].objective_metrics,
                {"completion_time_seconds": 10.0},
            )

    def test_select_pair_for_issue_requires_expected_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            create_solution(
                solutions_dir,
                judgments_dir,
                "issue-1/model-a/run-a",
                "issue-1",
                {"intent": 5, "correctness": 5, "scope": 5, "quality": 5},
            )

            with self.assertRaises(ValueError):
                select_pair_for_issue(
                    solutions_dir,
                    judgments_dir,
                    "issue-1",
                    judge_model="judge",
                    exposure="V1",
                    max_average_gap=0.75,
                    min_subscore_diversity=0.0,
                )

    def test_selects_and_saves_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            issue_id = "issue-1"
            for index, values in enumerate(
                [
                    (5, 5, 5, 5),
                    (4, 4, 4, 4),
                    (1, 1, 1, 1),
                ],
                start=1,
            ):
                create_solution(
                    solutions_dir,
                    judgments_dir,
                    f"{issue_id}/model-{index}/run-{index}",
                    issue_id,
                    {
                        "intent": values[0],
                        "correctness": values[1],
                        "scope": values[2],
                        "quality": values[3],
                    },
                    completion_time_seconds=10 + index,
                    step_count=index,
                )

            selected = select_pair_for_issue(
                solutions_dir,
                judgments_dir,
                issue_id,
                judge_model="judge",
                exposure="V1",
                max_average_gap=4,
                min_subscore_diversity=0.0,
                expected_solutions=3,
            )
            path = SelectionStorage(root / "selections").save(selected)

            self.assertEqual(selected.solution_a.solution_id, "model-1__run-1")
            self.assertEqual(selected.solution_a.model_slug, "model-1")
            self.assertEqual(selected.solution_a.run_id, "run-1")
            self.assertEqual(selected.solution_b.solution_id, "model-2__run-2")
            self.assertEqual(selected.selection_source, "scoring")
            self.assertEqual(selected.judge_model, "judge")
            self.assertTrue(path.exists())
            self.assertEqual(
                path.relative_to(root / "selections").as_posix(),
                f"{issue_id}/scoring__judge__V1_all.json",
            )
            run_id = selection_run_id(selected)
            self.assertEqual(
                SelectionStorage(root / "selections").load(issue_id, run_id),
                selected,
            )

    def test_saves_candidate_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            issue_id = "issue-1"
            for index, values in enumerate(
                [
                    (5, 1, 5, 1),
                    (1, 5, 1, 5),
                    (3, 3, 3, 3),
                ],
                start=1,
            ):
                create_solution(
                    solutions_dir,
                    judgments_dir,
                    f"{issue_id}/model-{index}/run-{index}",
                    issue_id,
                    {
                        "intent": values[0],
                        "correctness": values[1],
                        "scope": values[2],
                        "quality": values[3],
                    },
                )

            candidates = generate_candidates_for_issue(
                solutions_dir,
                judgments_dir,
                issue_id,
                judge_model="judge",
                exposure="V1",
                expected_solutions=3,
                max_average_gap=0.75,
                min_subscore_diversity=4,
            )
            run_id = selection_source_run_id("scoring", "judge", "V1")
            path = SelectionStorage(root / "selections").save_candidates(
                issue_id,
                run_id,
                candidates,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["issue_id"], issue_id)
            self.assertEqual(payload["run_id"], "scoring__judge__V1_all")
            self.assertEqual(payload["candidate_count"], 3)
            self.assertEqual(payload["feasible_count"], 3)
            self.assertIn("subscore_diversity", payload["candidates"][0])
            self.assertIn("scores", payload["candidates"][0]["solution_a"])

    def test_saves_global_selection_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            solutions_dir = root / "solutions"
            judgments_dir = root / "judgments"
            for issue_id in ["issue-1", "issue-2"]:
                for index, values in enumerate(
                    [
                        (5, 1, 5, 1),
                        (1, 5, 1, 5),
                    ],
                    start=1,
                ):
                    create_solution(
                        solutions_dir,
                        judgments_dir,
                        f"{issue_id}/model-{index}/run-{index}",
                        issue_id,
                        {
                            "intent": values[0],
                            "correctness": values[1],
                            "scope": values[2],
                            "quality": values[3],
                        },
                    )

            issue_candidates = {
                issue_id: generate_candidates_for_issue(
                    solutions_dir,
                    judgments_dir,
                    issue_id,
                    judge_model="judge",
                    exposure="V1",
                    max_average_gap=0.75,
                    min_subscore_diversity=0.0,
                    expected_solutions=2,
                )
                for issue_id in ["issue-1", "issue-2"]
            }
            result = select_balanced_pairs(
                issue_candidates,
                SelectionConfig(quality_bands={"all": (1.0, 5.0)}),
            )
            run_dir = SelectionStorage(root / "selections").save_global_run(
                "run-1",
                result,
            )

            self.assertTrue((run_dir / "config.json").exists())
            summary = json.loads((run_dir / "summary.json").read_text())
            self.assertEqual(summary["selection_method"], "greedy_balanced_v1")
            self.assertEqual(summary["issue_count"], 2)
            self.assertEqual(len(summary["selected_pairs"]), 2)
            self.assertTrue((run_dir / "candidates" / "issue-1.json").exists())
            selected = json.loads(
                (run_dir / "selected" / "issue-1.json").read_text()
            )
            self.assertEqual(selected["pair_count"], 1)
            self.assertIn("total_score", selected["pairs"][0])
            self.assertIn("score_components", selected["pairs"][0])
            self.assertEqual(selected["pairs"][0]["rank"], 1)


if __name__ == "__main__":
    unittest.main()
