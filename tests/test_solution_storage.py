import json
import tempfile
import unittest
from pathlib import Path

from src.models import Issue, Solution, SolutionInfo
from src.objective import ObjectiveMetrics
from src.storage import (
    SolutionStorage,
    iter_solution_paths,
    solution_id_from_path,
    solution_id_from_run_dir,
)


class SolutionStorageTest(unittest.TestCase):
    def test_saves_solution_under_issue_model_run_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue = Issue(
                issue_id="owner__repo-1",
                repo="owner/repo",
                number=1,
                title="Title",
                body="Body",
            )
            solution = Solution(
                issue_id=issue.issue_id,
                model="openai/gpt-4o",
                provider="openai",
                diff="diff --git a/a.py b/a.py",
                trajectory={},
                duration_ms=100,
                created_at="now",
            )
            info = SolutionInfo(
                summary="Changed a.py to fix the issue",
                objective_metrics=ObjectiveMetrics(
                    completion_time_seconds=0.1,
                    step_count=1,
                    raw_action_count=2,
                    model_call_count=3,
                ),
                exposed_files=["a.py"],
                grep_exposed_files=["tests/test_a.py"],
            )

            path = SolutionStorage(root).save(solution, issue, info)

            self.assertEqual(path.parent.parent.name, "owner__repo-1")
            self.assertEqual(path.parent.name, "openai_gpt-4o")
            self.assertTrue((path / "issue.json").exists())
            self.assertTrue((path / "solution.json").exists())
            self.assertTrue((path / "info.json").exists())
            self.assertTrue((path / "patch.diff").exists())
            self.assertFalse((path / "objective_metrics.json").exists())
            self.assertFalse((path / "exposed_files.json").exists())
            self.assertFalse((path / "grep_exposed_files.json").exists())
            saved_info = json.loads((path / "info.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_info["summary"], "Changed a.py to fix the issue")
            self.assertEqual(saved_info["exposed_files"], ["a.py"])
            self.assertEqual(saved_info["grep_exposed_files"], ["tests/test_a.py"])
            self.assertEqual(saved_info["objective_metrics"]["step_count"], 1)
            self.assertNotIn(
                "objective_metrics",
                (path / "solution.json").read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "summary",
                (path / "solution.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(iter_solution_paths(root), [path])
            self.assertEqual(iter_solution_paths(root, issue.issue_id), [path])
            self.assertEqual(iter_solution_paths(root, "missing-issue"), [])
            self.assertEqual(
                solution_id_from_run_dir(path),
                f"openai_gpt-4o__{path.name}",
            )
            self.assertEqual(
                solution_id_from_path(path),
                solution_id_from_run_dir(path),
            )
            with self.assertRaises(ValueError):
                solution_id_from_run_dir(path / "solution.json")


class SanitizedIssueIdTest(unittest.TestCase):
    def test_lookup_by_raw_issue_id_finds_sanitized_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_issue_id = "owner/repo#1"
            issue = Issue(
                issue_id=raw_issue_id,
                repo="owner/repo",
                number=1,
                title="Title",
                body="Body",
            )
            solution = Solution(
                issue_id=raw_issue_id,
                model="openai/gpt-4o",
                provider="openai",
                diff="diff --git a/a.py b/a.py",
                trajectory={},
                duration_ms=100,
                created_at="now",
            )
            folder = SolutionStorage(root).save(
                solution, issue, SolutionInfo(summary="")
            )

            self.assertEqual(folder.parent.parent.name, "owner_repo_1")
            found = iter_solution_paths(root, issue_id=raw_issue_id)
            self.assertEqual(found, [folder])


if __name__ == "__main__":
    unittest.main()
