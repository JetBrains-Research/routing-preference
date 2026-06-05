import json
import tempfile
import unittest
from pathlib import Path

from src.judge.loader import CharacteristicLoader, PromptLoader


class JudgeLoaderTests(unittest.TestCase):
    def test_characteristic_loader_uses_configured_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            judge_dir = Path(tmp)
            char_dir = judge_dir / "rubrics" / "intent_docs"
            char_dir.mkdir(parents=True)
            files = {
                "NAME.md": "Intent Understanding",
                "SHORT.md": "Short",
                "LONG.md": "Long",
                "SCORING_BASIS.md": "Scoring basis",
                "SCORING_STEPS_V1.md": "Scoring V1",
                "SCORING_STEPS_V2.md": "Scoring V2",
                "RANKING_BASIS.md": "Ranking basis",
                "RANKING_STEPS_V1.md": "Ranking V1",
                "RANKING_STEPS_V2.md": "Ranking V2",
            }
            for filename, content in files.items():
                (char_dir / filename).write_text(content, encoding="utf-8")
            (judge_dir / "prompts.json").write_text(
                json.dumps(
                    {
                        "characteristics": ["intent"],
                        "characteristic_paths": {
                            "intent": "./rubrics/intent_docs",
                        },
                        "characteristic_files": {
                            "name": "NAME.md",
                            "short_description": "SHORT.md",
                            "long_description": "LONG.md",
                            "scoring_basis": "SCORING_BASIS.md",
                            "scoring_steps_v1": "SCORING_STEPS_V1.md",
                            "scoring_steps_v2": "SCORING_STEPS_V2.md",
                            "ranking_basis": "RANKING_BASIS.md",
                            "ranking_steps_v1": "RANKING_STEPS_V1.md",
                            "ranking_steps_v2": "RANKING_STEPS_V2.md",
                        },
                        "characteristic_placeholders": {
                            "CHARACTERISTIC_NAME.md": "name",
                            "CHARACTERISTIC_SCORING_STEPS_V2.md": "scoring_steps_v2",
                            "CHARACTERISTIC_RANKING_BASIS.md": "ranking_basis",
                        },
                    }
                ),
                encoding="utf-8",
            )

            loaded = CharacteristicLoader(judge_dir).load("intent")

        self.assertEqual(loaded.name, "Intent Understanding")
        self.assertEqual(loaded.scoring_steps_v2, "Scoring V2")
        self.assertEqual(loaded.ranking_basis, "Ranking basis")

    def test_prompt_loader_uses_configured_prompt_and_context_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            judge_dir = Path(tmp)
            char_dir = judge_dir / "chars" / "intent"
            prompt_dir = judge_dir / "templates"
            context_dir = judge_dir / "ctx"
            char_dir.mkdir(parents=True)
            prompt_dir.mkdir()
            context_dir.mkdir()

            for filename in [
                "SHORT.md",
                "LONG.md",
                "SCORING_BASIS.md",
                "SCORING_STEPS_V1.md",
                "SCORING_STEPS_V2.md",
                "RANKING_BASIS.md",
                "RANKING_STEPS_V1.md",
                "RANKING_STEPS_V2.md",
            ]:
                (char_dir / filename).write_text(filename, encoding="utf-8")
            (char_dir / "NAME.md").write_text("Intent", encoding="utf-8")
            (prompt_dir / "single-score.md").write_text(
                "Prompt: <CHARACTERISTIC_NAME.md>",
                encoding="utf-8",
            )
            (context_dir / "score-v1.md").write_text("Context V1", encoding="utf-8")
            (judge_dir / "prompts.json").write_text(
                json.dumps(
                    {
                        "characteristics": ["intent"],
                        "characteristic_paths": {"intent": "./chars/intent"},
                        "characteristic_files": {
                            "name": "NAME.md",
                            "short_description": "SHORT.md",
                            "long_description": "LONG.md",
                            "scoring_basis": "SCORING_BASIS.md",
                            "scoring_steps_v1": "SCORING_STEPS_V1.md",
                            "scoring_steps_v2": "SCORING_STEPS_V2.md",
                            "ranking_basis": "RANKING_BASIS.md",
                            "ranking_steps_v1": "RANKING_STEPS_V1.md",
                            "ranking_steps_v2": "RANKING_STEPS_V2.md",
                        },
                        "characteristic_placeholders": {
                            "CHARACTERISTIC_NAME.md": "name",
                        },
                        "prompts": {
                            "scoring": {
                                "single": {
                                    "V1": "./templates/single-score.md",
                                },
                            },
                        },
                        "contexts": {
                            "scoring": {
                                "V1": "./ctx/score-v1.md",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            loader = PromptLoader(judge_dir)
            prompt = loader.load_single_prompt("scoring", "V1", "intent")
            context = loader.load_context("scoring", "V1")

        self.assertEqual(prompt, "Prompt: Intent")
        self.assertEqual(context, "Context V1")


if __name__ == "__main__":
    unittest.main()
