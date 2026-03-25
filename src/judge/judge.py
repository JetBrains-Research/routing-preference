"""Judge that scores a solution on all characteristics"""

from datetime import datetime

from src.models import Issue, Solution

from .characteristics import CHARACTERISTICS
from .models import Judgment, Score
from .scorer import CharacteristicScorer


class Judge:
    """Scores a solution on all characteristics"""

    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model
        self.scorer = CharacteristicScorer(model=model)

    def judge(
        self,
        issue: Issue,
        solution: Solution,
        solution_folder: str,
    ) -> Judgment:
        """Judge a solution on all characteristics.

        Args:
            issue: The original issue.
            solution: The generated solution.
            solution_folder: The folder name where the solution is stored.

        Returns:
            Complete Judgment with all scores.
        """
        scores: list[Score] = []
        for characteristic in CHARACTERISTICS:
            score = self.scorer.score(characteristic, issue, solution)
            scores.append(score)

        overall = sum(s.value for s in scores) / len(scores)

        return Judgment(
            solution_folder=solution_folder,
            issue_id=solution.issue_id,
            solution_model=solution.model,
            judge_model=self.model,
            scores=scores,
            overall_score=round(overall, 2),
            created_at=datetime.now().isoformat(),
        )
