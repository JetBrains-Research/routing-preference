"""Data models for the Judge."""

from dataclasses import dataclass


@dataclass
class Score:
    """Score for a single characteristic."""

    characteristic_id: str
    value: int
    reasoning: str


@dataclass
class Judgment:
    """Complete judgment of a solution."""

    solution_folder: str
    issue_id: str
    solution_model: str
    judge_model: str
    scores: list[Score]
    overall_score: float
    created_at: str
    exposure: str = "V1"
    basis: str = "scoring"
    granularity: str = "all"
    characteristic_id: str | None = None
    score_scale: tuple[int, int] | None = None
