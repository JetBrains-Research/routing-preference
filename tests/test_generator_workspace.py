"""Workspace preparation and diff capture for both task types."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from src.generator import SolutionGenerator
from src.models import Issue


def _zero_shot_issue():
    return Issue(issue_id="prompt__tool-1", title="Tool", body="Build a tool.")


def _github_issue():
    return Issue(
        issue_id="owner__repo-1",
        title="Bug",
        body="Fix it.",
        repo="owner/repo",
        number=1,
    )


class WorkspacePreparationTest(unittest.TestCase):
    def setUp(self):
        self.generator = SolutionGenerator(environment_type="local")

    def test_init_workspace_creates_git_repo_with_initial_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            self.generator._prepare_workspace(_zero_shot_issue(), workspace)

            self.assertTrue((workspace / ".git").is_dir())
            log = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(len(log.stdout.strip().splitlines()), 1)

    def test_capture_diff_includes_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            self.generator._init_workspace(workspace)
            (workspace / "tool.py").write_text("print('hi')\n", encoding="utf-8")

            diff = self.generator._capture_diff(workspace)

            self.assertIn("tool.py", diff)
            self.assertIn("print('hi')", diff)

    def test_capture_diff_includes_tracked_changes_and_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            self.generator._init_workspace(workspace)
            (workspace / "existing.py").write_text("old\n", encoding="utf-8")
            identity = [
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@localhost",
            ]
            subprocess.run(
                ["git", "add", "existing.py"],
                cwd=workspace,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", *identity, "commit", "-m", "add existing"],
                cwd=workspace,
                check=True,
                capture_output=True,
            )
            (workspace / "existing.py").write_text("new\n", encoding="utf-8")
            (workspace / "created.py").write_text("fresh\n", encoding="utf-8")

            diff = self.generator._capture_diff(workspace)

            self.assertIn("existing.py", diff)
            self.assertIn("created.py", diff)

    def test_init_workspace_seeds_assets_outside_the_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp) / "assets"
            assets.mkdir()
            (assets / "books.json").write_text("[]", encoding="utf-8")
            (assets / "nested").mkdir()
            (assets / "nested" / "data.csv").write_text("a,b\n", encoding="utf-8")

            workspace = Path(tmp) / "ws"
            issue = Issue(
                issue_id="prompt__books-1",
                title="Books",
                body="Load assets/books.json.",
                assets_dir=str(assets),
            )
            self.generator._prepare_workspace(issue, workspace)

            self.assertTrue((workspace / "assets" / "books.json").is_file())
            self.assertTrue((workspace / "assets" / "nested" / "data.csv").is_file())

            # Seeded files are committed, so an untouched workspace has no diff.
            self.assertEqual(self.generator._capture_diff(workspace), "")

            # Only agent-created files appear in the diff.
            (workspace / "app.py").write_text("app\n", encoding="utf-8")
            diff = self.generator._capture_diff(workspace)
            self.assertIn("app.py", diff)
            self.assertNotIn("books.json", diff)

    def test_init_workspace_fails_on_missing_assets_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            issue = Issue(
                issue_id="prompt__x-1",
                title="X",
                body="B",
                assets_dir=str(Path(tmp) / "does-not-exist"),
            )
            with self.assertRaises(RuntimeError):
                self.generator._prepare_workspace(issue, workspace)

    def test_workspace_name_falls_back_to_task_id(self):
        name = self.generator._make_workspace_name(_zero_shot_issue())
        self.assertTrue(name.startswith("prompt__tool-1_"))
        self.assertNotIn("None", name)

        name = self.generator._make_workspace_name(_github_issue())
        self.assertTrue(name.startswith("owner_repo_1_"))


class PromptTemplateTest(unittest.TestCase):
    def setUp(self):
        self.generator = SolutionGenerator(environment_type="local")

    def test_zero_shot_tasks_use_zero_shot_template(self):
        prompt = self.generator._build_prompt(_zero_shot_issue())
        self.assertIn("empty project directory", prompt)
        self.assertIn("Build a tool.", prompt)

    def test_github_issues_use_default_template(self):
        prompt = self.generator._build_prompt(_github_issue())
        self.assertNotIn("empty project directory", prompt)
        self.assertIn("Fix it.", prompt)


if __name__ == "__main__":
    unittest.main()
