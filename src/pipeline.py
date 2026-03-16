"""Pipeline orchestration for solution generation."""

from pathlib import Path

from .collector import IssueCollector
from .generator import SolutionGenerator
from .storage import SolutionStorage


class Pipeline:
    """Orchestrates the solution generation pipeline."""

    def __init__(
        self,
        solutions_dir: Path,
        litellm_base_url: str = "http://localhost:4000",
    ):
        self.collector = IssueCollector()
        self.generator = SolutionGenerator(litellm_base_url)
        self.storage = SolutionStorage(solutions_dir)

    def run_single(
        self,
        repo: str,
        issue_number: int,
        models: list[tuple[str, str]],
    ) -> None:
        """Generate solutions for a single issue with multiple models.

        Args:
            repo: Repository in "owner/repo" format.
            issue_number: The issue number to solve.
            models: List of (model_name, provider) tuples.
        """
        issue = self.collector.fetch(repo, issue_number)
        print(f"Fetched: {issue.title}")

        for model_name, provider in models:
            print(f"  Generating with {model_name} ({provider})...")
            solution = self.generator.generate(issue, model_name, provider)
            path = self.storage.save(solution)
            print(f"  Saved to {path.name} ({solution.duration_ms}ms)")

    def run_batch(
        self,
        repo: str,
        limit: int,
        models: list[tuple[str, str]],
    ) -> None:
        """Generate solutions for multiple issues.

        Args:
            repo: Repository in "owner/repo" format.
            limit: Maximum number of issues to fetch.
            models: List of (model_name, provider) tuples.
        """
        issues = self.collector.fetch_batch(repo, limit)
        print(f"Fetched {len(issues)} issues from {repo}")

        for issue in issues:
            print(f"\n[{issue.id}] {issue.title}")
            for model_name, provider in models:
                print(f"  Generating with {model_name} ({provider})...")
                try:
                    solution = self.generator.generate(issue, model_name, provider)
                    path = self.storage.save(solution)
                    print(f"  Saved to {path.name} ({solution.duration_ms}ms)")
                except Exception as e:
                    print(f"  Failed: {e}")
