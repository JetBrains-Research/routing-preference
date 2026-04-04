"""Data models for the solution generation pipeline."""

from dataclasses import dataclass, field


@dataclass
class Issue:
    """A GitHub issue to solve."""

    # Required fields
    issue_id: str
    repo: str
    number: int
    title: str
    body: str
    assigned_reviewer: str | None = None
    reviewer_type: str | None = None  # maintainer/author

    # Optional
    labels: list[str] = field(default_factory=list)
    base_commit: str | None = None
    issue_type: str | None = None  # bug/feature/other
    complexity: str | None = None  # simple/medium/complex
    created_at: str | None = None
    author: str | None = None
    html_url: str | None = None
    state: str | None = None  # open/closed
    comments_count: int | None = None
    reactions_count: int | None = None


@dataclass
class Solution:
    """A generated solution for an issue."""

    issue_id: str
    model: str
    provider: str
    diff: str
    trajectory: dict
    duration_ms: int
    created_at: str
