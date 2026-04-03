"""Routing Preference."""

# Lazy imports to avoid loading heavy dependencies (mini-swe-agent) when not needed
def __getattr__(name: str):
    if name == "IssueDataset":
        from .dataset import IssueDataset
        return IssueDataset
    if name == "SolutionGenerator":
        from .generator import SolutionGenerator
        return SolutionGenerator
    if name == "Issue":
        from .models import Issue
        return Issue
    if name == "Solution":
        from .models import Solution
        return Solution
    if name == "Pipeline":
        from .pipeline import Pipeline
        return Pipeline
    if name == "SolutionStorage":
        from .storage import SolutionStorage
        return SolutionStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Issue",
    "IssueDataset",
    "Pipeline",
    "Solution",
    "SolutionGenerator",
    "SolutionStorage",
]
