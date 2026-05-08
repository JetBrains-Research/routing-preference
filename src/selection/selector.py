"""Select solution pairs for comparison."""

from dataclasses import dataclass, field
from itertools import combinations
from math import sqrt

CHARACTERISTIC_ORDER = ("intent", "correctness", "scope", "quality")
OBJECTIVE_KEYS = ("completion_time_seconds", "step_count")


@dataclass(frozen=True)
class ScoredSolution:
    """A solution with subjective scores and optional objective metrics."""

    solution_id: str
    scores: dict[str, float]
    objective_metrics: dict[str, float] = field(default_factory=dict)
    model_slug: str | None = None
    run_id: str | None = None
    relative_path: str | None = None

    @property
    def score_vector(self) -> tuple[float, ...]:
        """Subjective score vector in canonical characteristic order."""
        missing = [cid for cid in CHARACTERISTIC_ORDER if cid not in self.scores]
        if missing:
            raise ValueError(
                f"Missing subjective scores for {self.solution_id}: {missing}"
            )
        return tuple(float(self.scores[cid]) for cid in CHARACTERISTIC_ORDER)

    @property
    def subjective_average(self) -> float:
        values = self.score_vector
        return sum(values) / len(values)


@dataclass(frozen=True)
class CandidatePair:
    """A candidate pair for the survey."""

    solution_a: ScoredSolution
    solution_b: ScoredSolution
    subjective_average: float
    subjective_average_gap: float
    subjective_profile_distance: float
    subscore_diversity: float
    objective_distance: float
    local_score: float
    feasible: bool

    @property
    def solution_ids(self) -> tuple[str, str]:
        return self.solution_a.solution_id, self.solution_b.solution_id


def generate_candidate_pairs(
    solutions: list[ScoredSolution],
    *,
    max_average_gap: float,
    min_subscore_diversity: float,
) -> list[CandidatePair]:
    """Generate all pair candidates and mark feasibility."""
    if len(solutions) < 2:
        raise ValueError("At least two scored solutions are required")

    return [
        _build_candidate(
            left,
            right,
            max_average_gap=max_average_gap,
            min_subscore_diversity=min_subscore_diversity,
        )
        for left, right in combinations(
            sorted(solutions, key=lambda s: s.solution_id),
            2,
        )
    ]


def select_best_pair(
    solutions: list[ScoredSolution],
    *,
    max_average_gap: float,
    min_subscore_diversity: float,
) -> CandidatePair:
    """Select the best pair from scored solutions.

    Prefer pairs with similar average scores,
    then choose the strongest profile difference within that close-enough set.
    If no pair is within max_average_gap, fall back to all pairs.
    """
    candidates = generate_candidate_pairs(
        solutions,
        max_average_gap=max_average_gap,
        min_subscore_diversity=min_subscore_diversity,
    )

    feasible_candidates = [candidate for candidate in candidates if candidate.feasible]
    if feasible_candidates:
        candidates = feasible_candidates

    return sorted(candidates, key=_candidate_sort_key)[0]


def _build_candidate(
    left: ScoredSolution,
    right: ScoredSolution,
    *,
    max_average_gap: float,
    min_subscore_diversity: float,
) -> CandidatePair:
    subjective_average_gap = abs(left.subjective_average - right.subjective_average)
    subscore_diversity = _manhattan_distance(left.score_vector, right.score_vector)
    subjective_profile_distance = _euclidean_distance(
        _centered_vector(left.score_vector),
        _centered_vector(right.score_vector),
    )
    local_score = subjective_profile_distance
    return CandidatePair(
        solution_a=left,
        solution_b=right,
        subjective_average=(left.subjective_average + right.subjective_average) / 2,
        subjective_average_gap=subjective_average_gap,
        subjective_profile_distance=subjective_profile_distance,
        subscore_diversity=subscore_diversity,
        objective_distance=_objective_distance(left, right),
        local_score=local_score,
        feasible=(
            subjective_average_gap <= max_average_gap
            and subscore_diversity >= min_subscore_diversity
        ),
    )


def _candidate_sort_key(candidate: CandidatePair) -> tuple:
    return (
        -round(candidate.subjective_profile_distance, 12),
        round(candidate.subjective_average_gap, 12),
        -round(candidate.objective_distance, 12),
        candidate.solution_ids,
    )


def _centered_vector(values: tuple[float, ...]) -> tuple[float, ...]:
    average = sum(values) / len(values)
    return tuple(value - average for value in values)


def _euclidean_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _manhattan_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right))


def _objective_distance(left: ScoredSolution, right: ScoredSolution) -> float:
    left_values = []
    right_values = []
    for key in OBJECTIVE_KEYS:
        if key not in left.objective_metrics or key not in right.objective_metrics:
            continue
        left_values.append(float(left.objective_metrics[key]))
        right_values.append(float(right.objective_metrics[key]))

    if not left_values:
        return 0.0

    return _euclidean_distance(tuple(left_values), tuple(right_values))
