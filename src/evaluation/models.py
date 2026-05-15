"""Models for comparing judge against manual scoring."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ScoreSet:
    scores: dict[str, int]
    overall_score: float
    path: Path


@dataclass(frozen=True)
class ScoringRun:
    """One scoring run folder to compare against manual scores."""

    id: str
    judge_slug: str
    exposure: str
    granularity: str
    folder: str


@dataclass(frozen=True)
class EvaluationSolution:
    issue_id: str
    solution_id: str
    solution_model: str
    empty_solution: bool
    solution_path: Path
    manual: ScoreSet
    judge_scores: dict[str, ScoreSet] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationDataset:
    solutions: list[EvaluationSolution]


@dataclass(frozen=True)
class EvaluationExportResult:
    path: Path
    row_count: int
    solution_count: int
    issue_count: int
