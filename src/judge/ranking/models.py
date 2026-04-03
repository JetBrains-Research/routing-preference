"""Data models for comparative ranking judge."""

from dataclasses import dataclass


@dataclass
class Ranking:
    """Ranking for a single characteristic across all solutions."""

    characteristic_id: str
    # Model name -> rank (1 = best, 2 = second best, etc.)
    ranks: dict[str, int]
    reasoning: str


@dataclass
class ComparativeJudgment:
    """Complete comparative judgment for all solutions of an issue."""

    issue_id: str
    solution_models: list[str]
    judge_model: str
    rankings: list[Ranking]  # One ranking per characteristic
    overall_ranks: dict[str, float]
    created_at: str
