import tempfile
import unittest
from pathlib import Path

from src.judge.models import (
    CharacteristicRanking,
    Ranking,
    RankingJudgment,
    Score,
    ScoringJudgment,
)
from src.judge.storage import (
    RankingStorage,
    ScoringStorage,
    judge_run_id,
    parse_judge_run_id,
    slugify_group_id,
    slugify_judge_model,
)


class JudgeStorageTest(unittest.TestCase):
    def test_judge_run_id_includes_model_and_variant(self):
        self.assertEqual(slugify_judge_model("openai/gpt-4o"), "openai_gpt-4o")
        self.assertEqual(slugify_group_id("issue/one"), "issue_one")
        self.assertEqual(
            judge_run_id("openai/gpt-4o", "V2.1", "single", "intent"),
            "openai_gpt-4o__V2.1_single",
        )
        self.assertEqual(
            parse_judge_run_id(
                "openai_gpt-4o__V2.1_single",
                ("intent", "correctness", "scope", "quality"),
            ),
            {
                "judge_slug": "openai_gpt-4o",
                "exposure": "V2.1",
                "granularity": "single",
                "characteristic_id": None,
            },
        )
        self.assertEqual(
            parse_judge_run_id(
                "openai_gpt-4o__V2.1_intent",
                ("intent", "correctness", "scope", "quality"),
            ),
            {
                "judge_slug": "openai_gpt-4o",
                "exposure": "V2.1",
                "granularity": "single",
                "characteristic_id": "intent",
            },
        )

    def test_scoring_storage_is_issue_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = ScoringStorage(Path(tmp))
            judgment = ScoringJudgment(
                solution_folder="solution-a",
                issue_id="issue-1",
                solution_model="model-a",
                judge_model="openai/gpt-4o",
                scores=[Score("intent", 5, "ok")],
                overall_score=5,
                created_at="now",
                exposure="V1",
                granularity="all",
                score_scale=(1, 5),
            )

            path = storage.save(judgment)

            self.assertEqual(
                path.relative_to(Path(tmp)).as_posix(),
                "issue-1/scoring/openai_gpt-4o__V1_all/solution-a.json",
            )
            loaded = storage.load(
                "issue-1",
                "solution-a",
                "openai/gpt-4o",
                "V1",
                "all",
            )
            self.assertEqual(loaded, judgment)

    def test_ranking_storage_is_issue_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = RankingStorage(Path(tmp))
            judgment = RankingJudgment(
                group_id="issue-1",
                issue_id="issue-1",
                solution_ids=["a", "b"],
                judge_model="openai/gpt-4o",
                rankings=[
                    CharacteristicRanking(
                        characteristic_id="intent",
                        rankings=[Ranking(1, "a"), Ranking(2, "b")],
                    )
                ],
                created_at="now",
                exposure="V1",
                granularity="all",
            )

            path = storage.save(judgment)

            self.assertEqual(
                path.relative_to(Path(tmp)).as_posix(),
                "issue-1/ranking/issue-1/openai_gpt-4o__V1_all.json",
            )
            loaded = storage.load("issue-1", "issue-1", "openai/gpt-4o", "V1", "all")
            self.assertEqual(loaded, judgment)

    def test_ranking_storage_distinguishes_groups_for_same_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = RankingStorage(Path(tmp))
            first = RankingJudgment(
                group_id="group-a",
                issue_id="issue-1",
                solution_ids=["a", "b"],
                judge_model="openai/gpt-4o",
                rankings=[
                    CharacteristicRanking(
                        characteristic_id="intent",
                        rankings=[Ranking(1, "a"), Ranking(2, "b")],
                    )
                ],
                created_at="now",
                exposure="V1",
                granularity="all",
            )
            second = RankingJudgment(
                group_id="group-b",
                issue_id="issue-1",
                solution_ids=["c", "d"],
                judge_model="openai/gpt-4o",
                rankings=[
                    CharacteristicRanking(
                        characteristic_id="intent",
                        rankings=[Ranking(1, "d"), Ranking(2, "c")],
                    )
                ],
                created_at="now",
                exposure="V1",
                granularity="all",
            )

            storage.save(first)
            storage.save(second)

            self.assertEqual(
                storage.load("issue-1", "group-a", "openai/gpt-4o", "V1", "all"),
                first,
            )
            self.assertEqual(
                storage.load("issue-1", "group-b", "openai/gpt-4o", "V1", "all"),
                second,
            )


if __name__ == "__main__":
    unittest.main()
