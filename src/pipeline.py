"""Pipeline for solution generation."""

import logging
from pathlib import Path

from .dataset import IssueDataset
from .generator import SolutionGenerator
from .models import Issue
from .storage import SolutionStorage

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, solutions_dir: Path, environment_type: str = "local"):
        self.generator = SolutionGenerator(environment_type=environment_type)
        self.storage = SolutionStorage(solutions_dir)

    def run(
        self,
        dataset: IssueDataset,
        models: list[str],
        limit: int | None = None,
    ) -> None:
        """Generate solutions for issues

        Args:
            dataset: issue dataset to process
            models: list of model names
            limit: max number of issues to process (default: all)
        """
        issues = list(dataset)
        if limit is not None:
            issues = issues[:limit]

        logger.info(
            "Processing %d issues with %d models",
            len(issues),
            len(models),
        )

        for issue in issues:
            self._process_issue(issue, models)

    def _process_issue(self, issue: Issue, models: list[str]) -> None:
        logger.info("Processing issue %s: %s", issue.issue_id, issue.title)

        for model in models:
            logger.info(
                "Generating solution",
                extra={"issue_id": issue.issue_id, "model": model},
            )
            try:
                solution, exposed_files = self.generator.generate(issue, model)
                path = self.storage.save(solution, issue, exposed_files)
                logger.info(
                    "Saved solution to %s (%dms)",
                    path.name,
                    solution.duration_ms,
                    extra={"issue_id": issue.issue_id, "model": model},
                )
            except Exception as e:
                logger.exception(
                    "Failed to generate solution: %s",
                    e,
                    extra={"issue_id": issue.issue_id, "model": model},
                )
