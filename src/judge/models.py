"""Data models for the LLM judge system."""

from dataclasses import dataclass


@dataclass
class Characteristic:
    """Definition of a characteristic to measure.

    Each characteristic has its own prompt template for the LLM judge.
    """

    id: str
    name: str
    description: str
    prompt_template: str


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
