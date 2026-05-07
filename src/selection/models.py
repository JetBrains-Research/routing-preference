"""Data models for selected answer pairs."""

from dataclasses import dataclass

from .selector import CandidatePair


@dataclass(frozen=True)
class SelectedPair:
    """Selected pair for one issue."""

    issue_id: str
    solution_a: str
    solution_b: str
    subjective_average_gap: float
    subjective_profile_distance: float
    objective_distance: float
    scoring_exposure: str
    scoring_granularity: str = "all"

    @classmethod
    def from_candidate(
        cls,
        issue_id: str,
        candidate: CandidatePair,
        *,
        scoring_exposure: str,
        scoring_granularity: str = "all",
    ) -> "SelectedPair":
        return cls(
            issue_id=issue_id,
            solution_a=candidate.solution_a.solution_id,
            solution_b=candidate.solution_b.solution_id,
            subjective_average_gap=candidate.subjective_average_gap,
            subjective_profile_distance=candidate.subjective_profile_distance,
            objective_distance=candidate.objective_distance,
            scoring_exposure=scoring_exposure,
            scoring_granularity=scoring_granularity,
        )
