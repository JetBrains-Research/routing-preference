import json
import tempfile
import unittest
from pathlib import Path

from src.dataset import load_issues
from src.models import TASK_TYPE_GITHUB_ISSUE, TASK_TYPE_ZERO_SHOT, Issue


def _write_dataset(folder: Path, rows: list[dict]) -> str:
    path = folder / "tasks.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return str(path)


class DatasetLoaderTest(unittest.TestCase):
    def test_loads_github_issue_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_dataset(
                Path(tmp),
                [
                    {
                        "id": "owner__repo-1",
                        "repo": "owner/repo",
                        "number": 1,
                        "title": "Title",
                        "body": "Body",
                        "base_commit": "abc123",
                    }
                ],
            )

            issues = list(load_issues(path))

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].repo, "owner/repo")
            self.assertEqual(issues[0].task_type, TASK_TYPE_GITHUB_ISSUE)
            self.assertEqual(issues[0].base_commit, "abc123")

    def test_loads_zero_shot_prompt_rows_without_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_dataset(
                Path(tmp),
                [
                    {
                        "id": "prompt__unit-converter-001",
                        "title": "Unit Converter CLI",
                        "body": "Build a CLI tool that converts units...",
                    }
                ],
            )

            issues = list(load_issues(path))

            self.assertEqual(len(issues), 1)
            self.assertIsNone(issues[0].repo)
            self.assertIsNone(issues[0].number)
            self.assertIsNone(issues[0].base_commit)
            self.assertEqual(issues[0].task_type, TASK_TYPE_ZERO_SHOT)

    def test_explicit_task_type_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_dataset(
                Path(tmp),
                [
                    {
                        "id": "prompt__x-1",
                        "title": "T",
                        "body": "B",
                        "task_type": "zero_shot",
                    }
                ],
            )

            issues = list(load_issues(path))

            self.assertEqual(issues[0].task_type, TASK_TYPE_ZERO_SHOT)


class IssueTaskTypeTest(unittest.TestCase):
    def test_task_type_derived_from_repo(self):
        with_repo = Issue(
            issue_id="a", title="t", body="b", repo="owner/repo", number=1
        )
        without_repo = Issue(issue_id="b", title="t", body="b")

        self.assertEqual(with_repo.task_type, TASK_TYPE_GITHUB_ISSUE)
        self.assertEqual(without_repo.task_type, TASK_TYPE_ZERO_SHOT)


if __name__ == "__main__":
    unittest.main()
