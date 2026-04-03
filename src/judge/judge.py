"""Judge that scores a solution on all characteristics."""

from datetime import datetime
from enum import Enum

from ..models import Issue, Solution

from .batch_scorer import BatchScorer
from .models import Judgment, Score
from .prompt_scorer import PromptScorer


class ScoringMode(Enum):
    """Scoring mode for the judge."""

    SINGLE = "single"  # One LLM call per characteristic
    BATCH = "batch"  # One LLM call for all characteristics


class Judge:
    """Scores a solution on all characteristics."""

    def __init__(
        self,
        model: str = "openai/gpt-4o",
        mode: ScoringMode = ScoringMode.BATCH,
        prompt_version: str | None = None,
    ):
        self.model = model
        self.mode = mode

        if mode == ScoringMode.SINGLE:
            self.prompt_version = prompt_version or "V2.1"
            self.scorer = PromptScorer(
                model=model,
                prompt_version=self.prompt_version,
            )
        else:
            self.prompt_version = prompt_version or "V1"
            self.batch_scorer = BatchScorer(
                model=model,
                prompt_version=self.prompt_version,
            )

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
        if self.mode == ScoringMode.BATCH:
            scores = self.batch_scorer.score_all(issue, solution)
        else:
            scores = self._score_individually(issue, solution)

        overall = sum(s.value for s in scores) / len(scores) if scores else 0

        return Judgment(
            solution_folder=solution_folder,
            issue_id=solution.issue_id,
            solution_model=solution.model,
            judge_model=self.model,
            scores=scores,
            overall_score=round(overall, 2),
            created_at=datetime.now().isoformat(),
            prompt_version=self.prompt_version,
            score_scale=(1, 5),
        )

    def _score_individually(self, issue: Issue, solution: Solution) -> list[Score]:
        """Score each characteristic with separate LLM calls."""
        scores = []
        for char_id in BatchScorer.CHARACTERISTIC_ORDER:
            score = self.scorer.score(char_id, issue, solution)
            scores.append(score)
        return scores
