"""Pipeline orchestration for solution generation."""

from pathlib import Path

from .dataset import IssueDataset
from .generator import SolutionGenerator
from .models import Issue
from .storage import SolutionStorage


class Pipeline:
    """Orchestrates the solution generation pipeline."""

    def __init__(self, solutions_dir: Path):
        self.generator = SolutionGenerator()
        self.storage = SolutionStorage(solutions_dir)

    def run(
        self,
        dataset: IssueDataset,
        models: list[str],
        limit: int | None = None,
    ) -> None:
        """Generate solutions for issues in a dataset.

        Args:
            dataset: The issue dataset to process.
            models: List of model names (e.g., "anthropic/claude-sonnet-4-5-20250929").
            limit: Maximum number of issues to process (default: all).
        """
        issues = list(dataset)
        if limit:
            issues = issues[:limit]

        print(f"Processing {len(issues)} issues with {len(models)} models")

        for issue in issues:
            self._process_issue(issue, models)

    def run_single(self, issue: Issue, models: list[str]) -> None:
        """Generate solutions for a single issue.

        Args:
            issue: The issue to solve.
            models: List of model names.
        """
        self._process_issue(issue, models)

    def _process_issue(self, issue: Issue, models: list[str]) -> None:
        """Process a single issue with multiple models."""
        print(f"\n[{issue.id}] {issue.title}")

        for model in models:
            print(f"  Generating with {model}...")
            try:
                solution = self.generator.generate(issue, model)
                path = self.storage.save(solution)
                print(f"  Saved to {path.name} ({solution.duration_ms}ms)")
            except Exception as e:
                print(f"  Failed: {e}")
