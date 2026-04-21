"""Judge that scores a solution on all characteristics."""

from datetime import datetime

from ...models import Issue, Solution
from ..models import Judgment
from .v1 import Scorer as V1Scorer
from .v2 import Scorer as V2Scorer


class Judge:
    """Scores a solution on one or all characteristics."""

    def __init__(self, model: str = "openai/gpt-4o", exposure: str = "V1"):
        self.model = model
        self.exposure = exposure

        if exposure == "V1":
            self.scorer = V1Scorer(model=model)
        else:
            self.scorer = V2Scorer(model=model, exposure=exposure)

    def judge(
        self,
        issue: Issue,
        solution: Solution,
        solution_folder: str,
        source_files: dict[str, str] | None = None,
    ) -> Judgment:
        """Judge a solution on all characteristics (batch mode)."""
        if self.exposure == "V1":
            scores = self.scorer.score_all(issue, solution)
        else:
            if source_files is None:
                raise ValueError("V2 scoring requires source_files")
            scores = self.scorer.score_all(issue, solution, source_files)

        overall = sum(s.value for s in scores) / len(scores) if scores else 0

        return Judgment(
            solution_folder=solution_folder,
            issue_id=solution.issue_id,
            solution_model=solution.model,
            judge_model=self.model,
            scores=scores,
            overall_score=round(overall, 2),
            created_at=datetime.now().isoformat(),
            exposure=self.exposure,
            basis="scoring",
            granularity="all",
            characteristic_id=None,
            score_scale=(1, 5),
        )

    def judge_single(
        self,
        characteristic_id: str,
        issue: Issue,
        solution: Solution,
        solution_folder: str,
        source_files: dict[str, str] | None = None,
    ) -> Judgment:
        """Judge a solution on a single characteristic."""
        if self.exposure == "V1":
            score = self.scorer.score_single(characteristic_id, issue, solution)
        else:
            if source_files is None:
                raise ValueError("V2 scoring requires source_files")
            score = self.scorer.score_single(
                characteristic_id, issue, solution, source_files
            )

        return Judgment(
            solution_folder=solution_folder,
            issue_id=solution.issue_id,
            solution_model=solution.model,
            judge_model=self.model,
            scores=[score],
            overall_score=float(score.value),
            created_at=datetime.now().isoformat(),
            exposure=self.exposure,
            basis="scoring",
            granularity="single",
            characteristic_id=characteristic_id,
            score_scale=(1, 5),
        )
