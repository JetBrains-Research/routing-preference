import json
import tempfile
import unittest
from pathlib import Path

from src.cli import _load_issue


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


if __name__ == "__main__":
    unittest.main()
