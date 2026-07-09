"""Tests for the G1 greenfield judge exposure."""

import tempfile
import unittest
from pathlib import Path

from src.judge.loader import CharacteristicLoader, PromptLoader
from src.judge.scoring.v2.scorer import Scorer as V2Scorer
from src.judge.source_files import load_asset_files
from src.models import Issue, Solution


class G1PromptTest(unittest.TestCase):
    def test_characteristics_have_g1_steps(self):
        loader = CharacteristicLoader()
        for cid in loader.list_characteristics():
            char = loader.load(cid)
            self.assertTrue(
                char.scoring_steps_g1.strip(),
                f"Missing G1 scoring steps for {cid}",
            )

    def test_g1_all_prompt_hydrates_without_leftover_placeholders(self):
        loader = PromptLoader()
        prompt = loader.load_all_prompt(basis="scoring", exposure="G1")
        self.assertIn("task description", prompt)
        self.assertNotIn("GitHub issue", prompt)
        self.assertNotIn("CHARACTERISTIC_", prompt)

    def test_g1_context_uses_task_framing(self):
        context = PromptLoader().load_context(basis="scoring", exposure="G1")
        self.assertIn("## Task", context)
        self.assertIn("## Provided Starting Files", context)
        self.assertIn("<SOURCE_FILES>", context)

    def test_g1_single_and_ranking_are_not_registered(self):
        loader = PromptLoader()
        with self.assertRaises(ValueError):
            loader.load_single_prompt(
                basis="scoring", exposure="G1", characteristic_id="intent"
            )
        with self.assertRaises(ValueError):
            loader.load_all_prompt(basis="ranking", exposure="G1")

    def test_g1_scorer_builds_prompt_with_assets(self):
        issue = Issue(issue_id="prompt__x-1", title="Tool", body="Build a tool.")
        solution = Solution(
            issue_id="prompt__x-1",
            model="m/model",
            provider="m",
            diff="diff --git a/tool.py b/tool.py",
            trajectory={},
            duration_ms=1,
            created_at="now",
        )
        scorer = V2Scorer(exposure="G1")
        prompt = scorer._build_all_prompt(
            issue, solution, {"assets/data.csv": "a,b\n1,2\n"}
        )
        self.assertIn("assets/data.csv", prompt)
        self.assertIn("## Task", prompt)


class LoadAssetFilesTest(unittest.TestCase):
    def test_loads_files_relative_to_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp) / "assets"
            (assets / "nested").mkdir(parents=True)
            (assets / "books.json").write_text("[]", encoding="utf-8")
            (assets / "nested" / "data.csv").write_text("a,b\n", encoding="utf-8")

            files = load_asset_files(str(assets))

            self.assertEqual(
                sorted(files), ["assets/books.json", "assets/nested/data.csv"]
            )

    def test_skips_oversized_and_binary_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp) / "assets"
            assets.mkdir()
            (assets / "big.txt").write_text("x" * 1000, encoding="utf-8")
            (assets / "binary.bin").write_bytes(b"\xff\xfe\x00\x01")
            (assets / "ok.txt").write_text("fine", encoding="utf-8")

            files = load_asset_files(str(assets), max_file_bytes=100)

            self.assertEqual(sorted(files), ["assets/ok.txt"])

    def test_respects_total_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = Path(tmp) / "assets"
            assets.mkdir()
            (assets / "a.txt").write_text("x" * 80, encoding="utf-8")
            (assets / "b.txt").write_text("y" * 80, encoding="utf-8")

            files = load_asset_files(
                str(assets), max_file_bytes=100, max_total_bytes=100
            )

            self.assertEqual(len(files), 1)

    def test_missing_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_asset_files("/nonexistent/assets")


if __name__ == "__main__":
    unittest.main()
