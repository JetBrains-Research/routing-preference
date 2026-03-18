"""Data models for the solution generation pipeline."""

from dataclasses import dataclass


@dataclass
class Issue:
    """A GitHub issue to solve."""

    id: str
    repo: str
    number: int
    title: str
    body: str
    labels: list[str]
    base_commit: str | None = None


@dataclass
class Solution:
    """A generated solution for an issue."""

    issue_id: str
    model: str
    provider: str
    diff: str
    output: str
    duration_ms: int
    created_at: str
