"""Models for comparing judge against manual scoring."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ScoreSet:
    scores: dict[str, int]
    overall_score: float


@dataclass(frozen=True)
class ManualScoreSet(ScoreSet):
    path: Path


@dataclass(frozen=True)
class ScoringRunGroup:
    """One scoring variant to compare against manual scores.

    For granularity="all", `folders` contains one run folder.
    For granularity="single", `folders` contains one folder per characteristic.
    """

    id: str
    judge_slug: str
    exposure: str
    granularity: str
    folders: dict[str | None, str]


@dataclass(frozen=True)
class JudgeScoreSet(ScoreSet):
    run_group_id: str
    judge_slug: str
    exposure: str
    granularity: str
    paths: dict[str | None, Path]


@dataclass(frozen=True)
class EvaluationSolution:
    issue_id: str
    solution_id: str
    solution_model: str
    empty_solution: bool
    solution_path: Path
    manual: ManualScoreSet
    judge_scores: dict[str, JudgeScoreSet] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationDataset:
    solutions: list[EvaluationSolution]
