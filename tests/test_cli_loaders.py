import json
import tempfile
import unittest
from pathlib import Path

from src.cli import _gather_source_files, _load_issue
from src.models import Issue, Solution


class CliLoaderTest(unittest.TestCase):
    def test_load_issue_ignores_collection_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "issue.json").write_text(
                json.dumps(
                    {
                        "id": "owner__repo-1",
                        "repo": "owner/repo",
                        "number": 1,
                        "title": "Title",
                        "body": "Body",
                        "assigned_reviewer": "reviewer",
                    }
                ),
                encoding="utf-8",
            )

            issue = _load_issue(folder)

            self.assertEqual(issue.issue_id, "owner__repo-1")
            self.assertEqual(issue.repo, "owner/repo")
            self.assertFalse(hasattr(issue, "assigned_reviewer"))


class GatherSourceFilesTest(unittest.TestCase):
    def _solution(self, issue_id):
        return Solution(
            issue_id=issue_id,
            model="m/model",
            provider="m",
            diff="diff --git a/tool.py b/tool.py",
            trajectory={},
            duration_ms=1,
            created_at="now",
        )

    def test_v1_returns_none(self):
        issue = Issue(issue_id="prompt__x-1", title="t", body="b")
        result = _gather_source_files(
            "V1", Path("unused"), issue, self._solution(issue.issue_id)
        )
        self.assertIsNone(result)

    def test_v2_returns_empty_for_zero_shot_tasks(self):
        issue = Issue(issue_id="prompt__x-1", title="t", body="b")
        result = _gather_source_files(
            "V2.1", Path("unused"), issue, self._solution(issue.issue_id)
        )
        self.assertEqual(result, {})

    def test_v2_still_requires_base_commit_for_github_issues(self):
        issue = Issue(
            issue_id="owner__repo-1",
            title="t",
            body="b",
            repo="owner/repo",
            number=1,
        )
        with self.assertRaises(ValueError):
            _gather_source_files(
                "V2.1", Path("unused"), issue, self._solution(issue.issue_id)
            )


if __name__ == "__main__":
    unittest.main()
