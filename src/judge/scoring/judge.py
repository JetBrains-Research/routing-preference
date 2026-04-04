"""Judge that scores a solution on all characteristics."""

from datetime import datetime

from ...models import Issue, Solution
from ..models import Judgment, Score
from .v1 import Scorer as V1Scorer
from .v2 import Scorer as V2Scorer


class Judge:
    """Scores a solution on all characteristics."""

    def __init__(self, model: str = "openai/gpt-4o", version: str = "V1"):
        self.model = model
        self.version = version

        if version == "V1":
            self.scorer = V1Scorer(model=model)
        else:
            self.scorer = V2Scorer(model=model, prompt_version=version)

    def judge(
        self,
        issue: Issue,
        solution: Solution,
        solution_folder: str,
        source_files: dict[str, str] | None = None,
    ) -> Judgment:
        """Judge a solution on all characteristics.

        Args:
            issue: The issue being solved.
            solution: The proposed solution.
            solution_folder: Folder name where solution is stored.
            source_files: Required for V2 - dict of filepath -> content.
        """
        if self.version == "V1":
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
            prompt_version=self.version,
            score_scale=(1, 5),
        )

    def judge_single(
        self,
        characteristic_id: str,
        issue: Issue,
        solution: Solution,
        source_files: dict[str, str] | None = None,
    ) -> Score:
        """Judge a solution on a single characteristic.

        Args:
            characteristic_id: The characteristic to score (e.g., "intent", "correctness").
            issue: The issue being solved.
            solution: The proposed solution.
            source_files: Required for V2 - dict of filepath -> content.

        Returns:
            Score for the specified characteristic.
        """
        if self.version == "V1":
            return self.scorer.score_single(characteristic_id, issue, solution)
        else:
            if source_files is None:
                raise ValueError("V2 scoring requires source_files")
            return self.scorer.score_single(characteristic_id, issue, solution, source_files)
