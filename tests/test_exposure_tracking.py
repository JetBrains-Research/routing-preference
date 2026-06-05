import tempfile
import unittest
from pathlib import Path

from minisweagent.exceptions import Submitted
from minisweagent.environments.local import (
    LocalEnvironment,
    _extract_exposed_files,
)


class ExposureTrackingTest(unittest.TestCase):
    def test_extracts_full_file_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

            exposed_files, grep_exposed_files = _extract_exposed_files(
                "cat ./src/app.py", "print('hello')\n", str(root)
            )

            self.assertEqual(exposed_files, ["src/app.py"])
            self.assertEqual(grep_exposed_files, [])

    def test_extracts_numbered_file_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rich").mkdir()
            (root / "rich" / "progress.py").write_text(
                "class Progress: ...\n", encoding="utf-8"
            )

            exposed_files, grep_exposed_files = _extract_exposed_files(
                "nl -ba rich/progress.py | sed -n '1480,1520p'",
                "  1480 class Progress: ...\n",
                str(root),
            )

            self.assertEqual(exposed_files, ["rich/progress.py"])
            self.assertEqual(grep_exposed_files, [])

    def test_separates_grep_output_from_full_file_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rich").mkdir()
            (root / "tests").mkdir()
            (root / "rich" / "file_proxy.py").write_text(
                "class FileProxy: ...\n", encoding="utf-8"
            )
            (root / "tests" / "test_console.py").write_text(
                "FileProxy()\n", encoding="utf-8"
            )

            exposed_files, grep_exposed_files = _extract_exposed_files(
                'grep -R "FileProxy" .',
                "./rich/file_proxy.py:1:class FileProxy: ...\n"
                "./tests/test_console.py:1:FileProxy()\n",
                str(root),
            )

            self.assertEqual(exposed_files, [])
            self.assertEqual(
                grep_exposed_files,
                ["rich/file_proxy.py", "tests/test_console.py"],
            )

    def test_ignores_line_number_only_grep_output(self):
        exposed_files, grep_exposed_files = _extract_exposed_files(
            'grep -n "reset" tests/test_progress.py | head -20',
            "465:def test_reset() -> None:\n474:    progress.reset(\n",
            "",
        )

        self.assertEqual(exposed_files, [])
        self.assertEqual(grep_exposed_files, [])

    def test_skips_writes_and_non_repo_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

            exposed_files, grep_exposed_files = _extract_exposed_files(
                "cat <<'EOF' > src/app.py\nchanged\nEOF; cat /tmp/out.txt; cat .",
                "",
                str(root),
            )

            self.assertEqual(exposed_files, [])
            self.assertEqual(grep_exposed_files, [])

    def test_environment_serializes_both_exposure_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

            env = LocalEnvironment(cwd=str(root))
            env.execute({"command": "cat src/app.py"})
            env.execute({"command": 'grep -R "hello" .'})

            self.assertEqual(env.exposed_files, ["src/app.py"])
            self.assertEqual(env.grep_exposed_files, ["src/app.py"])
            self.assertEqual(env.serialize()["info"]["exposed_files"], ["src/app.py"])
            self.assertEqual(
                env.serialize()["info"]["grep_exposed_files"],
                ["src/app.py"],
            )

    def test_environment_accepts_submission_summary(self):
        env = LocalEnvironment()

        with self.assertRaises(Submitted) as context:
            env.execute(
                {
                    "command": (
                        'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT '
                        '"Changed parser handling"'
                    )
                }
            )

        message = context.exception.messages[0]
        self.assertEqual(message["role"], "exit")
        self.assertEqual(message["extra"]["submission"], "Changed parser handling")


if __name__ == "__main__":
    unittest.main()
