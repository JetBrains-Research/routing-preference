"""Top-level Judge that handles both scoring and ranking."""

from datetime import datetime

from ..models import Issue, Solution
from .models import (
    CharacteristicRanking,
    ScoringJudgment,
    RankingJudgment,
)
from .ranking import V1Ranker, V2Ranker
from .scoring import V1Scorer, V2Scorer


class Judge:
    """Judges solutions via scoring (per-solution) or ranking (across N solutions)."""

    def __init__(self, model: str = "openai/gpt-4o", exposure: str = "V1"):
        self.model = model
        self.exposure = exposure

        if exposure == "V1":
            self.scorer = V1Scorer(model=model)
            self.ranker = V1Ranker(model=model)
        else:
            self.scorer = V2Scorer(model=model, exposure=exposure)
            self.ranker = V2Ranker(model=model, exposure=exposure)

    # ----- Scoring -----

    def judge(
        self,
        issue: Issue,
        solution: Solution,
        solution_folder: str,
        source_files: dict[str, str] | None = None,
    ) -> ScoringJudgment:
        """Score a solution on all characteristics."""
        if self.exposure == "V1":
            scores = self.scorer.score_all(issue, solution)
        else:
            if source_files is None:
                raise ValueError("V2 scoring requires source_files")
            scores = self.scorer.score_all(issue, solution, source_files)

        overall = sum(s.value for s in scores) / len(scores) if scores else 0

        return ScoringJudgment(
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
    ) -> ScoringJudgment:
        """Score a solution on a single characteristic."""
        if self.exposure == "V1":
            score = self.scorer.score_single(characteristic_id, issue, solution)
        else:
            if source_files is None:
                raise ValueError("V2 scoring requires source_files")
            score = self.scorer.score_single(
                characteristic_id, issue, solution, source_files
            )

        return ScoringJudgment(
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

    # ----- Ranking -----

    def rank(
        self,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
        group_id: str,
        source_files_per_solution: list[dict[str, str]] | None = None,
    ) -> RankingJudgment:
        """Rank N solutions on all characteristics."""
        if self.exposure == "V1":
            results = self.ranker.rank_all(issue, solutions, solution_ids)
        else:
            if source_files_per_solution is None:
                raise ValueError("V2 ranking requires source_files_per_solution")
            results = self.ranker.rank_all(
                issue, solutions, solution_ids, source_files_per_solution
            )
        return self._wrap_ranking(
            results,
            issue=issue,
            solutions=solutions,
            solution_ids=solution_ids,
            group_id=group_id,
            granularity="all",
            characteristic_id=None,
        )

    def rank_single(
        self,
        characteristic_id: str,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
        group_id: str,
        source_files_per_solution: list[dict[str, str]] | None = None,
    ) -> RankingJudgment:
        """Rank N solutions on a single characteristic."""
        if self.exposure == "V1":
            result = self.ranker.rank_single(
                characteristic_id, issue, solutions, solution_ids
            )
        else:
            if source_files_per_solution is None:
                raise ValueError("V2 ranking requires source_files_per_solution")
            result = self.ranker.rank_single(
                characteristic_id,
                issue,
                solutions,
                solution_ids,
                source_files_per_solution,
            )
        return self._wrap_ranking(
            [result],
            issue=issue,
            solutions=solutions,
            solution_ids=solution_ids,
            group_id=group_id,
            granularity="single",
            characteristic_id=characteristic_id,
        )

    def _wrap_ranking(
        self,
        rankings: list[CharacteristicRanking],
        *,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
        group_id: str,
        granularity: str,
        characteristic_id: str | None,
    ) -> RankingJudgment:
        return RankingJudgment(
            group_id=group_id,
            issue_id=issue.issue_id,
            solution_ids=solution_ids,
            judge_model=self.model,
            rankings=rankings,
            created_at=datetime.now().isoformat(),
            exposure=self.exposure,
            basis="ranking",
            granularity=granularity,
            characteristic_id=characteristic_id,
            solution_models=[s.model for s in solutions],
        )
