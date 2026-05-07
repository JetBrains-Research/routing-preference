"""Data models for the Judge."""

from dataclasses import dataclass, field


@dataclass
class Score:
    """Score for a single characteristic (scoring basis)."""

    characteristic_id: str
    value: int
    reasoning: str


@dataclass
class ScoringJudgment:
    """Complete scoring judgment of a single solution."""

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


@dataclass
class Ranking:
    """One position in a ranking — pairs a rank with a solution id."""

    rank: int
    solution_id: str


@dataclass
class CharacteristicRanking:
    """The complete ordering of solutions for a single characteristic."""

    characteristic_id: str
    rankings: list[Ranking]


@dataclass
class RankingJudgment:
    """Complete ranking judgment over a group of solutions.

    Spans multiple solutions, identified by their solution folder names.
    For granularity="all", `rankings` contains one CharacteristicRanking per characteristic.
    For granularity="single", it contains exactly one, matching `characteristic_id`.
    """

    group_id: str
    issue_id: str
    solution_ids: list[str]
    judge_model: str
    rankings: list[CharacteristicRanking]
    created_at: str
    exposure: str = "V1"
    basis: str = "ranking"
    granularity: str = "all"
    characteristic_id: str | None = None
    solution_models: list[str] = field(default_factory=list)
