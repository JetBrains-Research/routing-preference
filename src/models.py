"""Data models for the solution generation pipeline."""

from dataclasses import dataclass, field

from .objective import ObjectiveMetrics

TASK_TYPE_GITHUB_ISSUE = "github_issue"
TASK_TYPE_ZERO_SHOT = "zero_shot"


@dataclass
class Issue:
    """A task to solve: a GitHub issue or a zero-shot project prompt.

    Zero-shot prompts have no repository; `title` names the task and `body`
    holds the full prompt text.
    """

    # Required fields
    issue_id: str
    title: str
    body: str

    # GitHub fields, absent for zero-shot prompts
    repo: str | None = None
    number: int | None = None

    # Derived from repo when not set explicitly
    task_type: str | None = None

    # Directory copied into the workspace before the agent runs (zero-shot
    # tasks whose prompt references provided data files)
    assets_dir: str | None = None

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

    def __post_init__(self) -> None:
        if self.task_type is None:
            self.task_type = (
                TASK_TYPE_GITHUB_ISSUE if self.repo else TASK_TYPE_ZERO_SHOT
            )


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


@dataclass
class SolutionInfo:
    """Run metadata stored next to a generated solution."""

    summary: str
    objective_metrics: ObjectiveMetrics | None = None
    exposed_files: list[str] = field(default_factory=list)
    grep_exposed_files: list[str] = field(default_factory=list)
