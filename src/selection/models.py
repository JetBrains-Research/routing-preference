"""Data models for selected solution pairs."""

from dataclasses import dataclass

from .selector import CandidatePair, ScoredSolution


@dataclass(frozen=True)
class SelectedSolution:
    """Reference to one selected solution run."""

    solution_id: str
    model_slug: str
    run_id: str
    relative_path: str


@dataclass(frozen=True)
class SelectedPair:
    """Selected pair for one issue."""

    issue_id: str
    solution_a: SelectedSolution
    solution_b: SelectedSolution
    subjective_average_gap: float
    subjective_profile_distance: float
    objective_distance: float
    selection_source: str
    judge_model: str
    judge_exposure: str
    judge_granularity: str = "all"
    judge_characteristic: str | None = None

    @classmethod
    def from_candidate(
        cls,
        issue_id: str,
        candidate: CandidatePair,
        *,
        selection_source: str,
        judge_model: str,
        judge_exposure: str,
        judge_granularity: str = "all",
        judge_characteristic: str | None = None,
    ) -> "SelectedPair":
        return cls(
            issue_id=issue_id,
            solution_a=_selected_solution(candidate.solution_a),
            solution_b=_selected_solution(candidate.solution_b),
            subjective_average_gap=candidate.subjective_average_gap,
            subjective_profile_distance=candidate.subjective_profile_distance,
            objective_distance=candidate.objective_distance,
            selection_source=selection_source,
            judge_model=judge_model,
            judge_exposure=judge_exposure,
            judge_granularity=judge_granularity,
            judge_characteristic=judge_characteristic,
        )


def _selected_solution(solution: ScoredSolution) -> SelectedSolution:
    if not solution.model_slug or not solution.run_id or not solution.relative_path:
        raise ValueError(f"Missing solution reference metadata: {solution.solution_id}")
    return SelectedSolution(
        solution_id=solution.solution_id,
        model_slug=solution.model_slug,
        run_id=solution.run_id,
        relative_path=solution.relative_path,
    )
