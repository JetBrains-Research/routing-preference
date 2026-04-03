"""Comparative judge that ranks all solutions for an issue."""

from datetime import datetime

from ...models import Issue, Solution
from ..loader import CharacteristicLoader
from .models import ComparativeJudgment, Ranking
from .scorer import RankingScorer


class RankingJudge:
    """Ranks all solutions for an issue on all characteristics."""

    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model
        self.scorer = RankingScorer(model=model)
        self.char_loader = CharacteristicLoader()

    def judge(
        self,
        issue: Issue,
        solutions: list[Solution],
    ) -> ComparativeJudgment:
        characteristics = self.char_loader.load_all()

        rankings: list[Ranking] = []
        for characteristic in characteristics:
            ranking = self.scorer.rank(characteristic, issue, solutions)
            rankings.append(ranking)

        overall_ranks = self._calculate_overall_ranks(rankings, solutions)

        return ComparativeJudgment(
            issue_id=issue.issue_id,
            solution_models=[s.model for s in solutions],
            judge_model=self.model,
            rankings=rankings,
            overall_ranks=overall_ranks,
            created_at=datetime.now().isoformat(),
        )

    def _calculate_overall_ranks(
        self,
        rankings: list[Ranking],
        solutions: list[Solution],
    ) -> dict[str, float]:
        totals: dict[str, float] = {s.model: 0.0 for s in solutions}

        for ranking in rankings:
            for model, rank in ranking.ranks.items():
                totals[model] += rank

        num_characteristics = len(rankings)
        return {
            model: round(total / num_characteristics, 2)
            for model, total in totals.items()
        }
