"""Pipeline for batch judging solutions."""

import json
import logging
from pathlib import Path

from .models import Issue, Solution

from .judge.judge import Judge, ScoringMode
from .judge.storage import JudgmentStorage

logger = logging.getLogger(__name__)


class JudgePipeline:
    """Orchestrates judging multiple solutions."""

    def __init__(
        self,
        solutions_dir: Path,
        judge_model: str = "openai/gpt-4o",
        mode: str = "batch",
        prompt_version: str | None = None,
    ):
        self.solutions_dir = solutions_dir
        self.judge = Judge(
            model=judge_model,
            mode=ScoringMode(mode),
            prompt_version=prompt_version,
        )
        self.storage = JudgmentStorage(solutions_dir)

    def run(self, skip_existing: bool = True) -> None:
        """Judge all solutions in the storage directory.

        Args:
            skip_existing: Skip solutions that already have judgments.
        """
        folders = self._list_solution_folders(skip_existing)
        logger.info("Found %d solutions to judge", len(folders))

        for folder in folders:
            self._judge_solution(folder)

    def run_single(self, solution_folder: str) -> None:
        """Judge a single solution by folder name."""
        self._judge_solution(solution_folder)

    def _list_solution_folders(self, skip_existing: bool) -> list[str]:
        """List solution folders to process."""
        if skip_existing:
            return self.storage.list_unjudged()

        folders = []
        for folder in sorted(self.solutions_dir.iterdir()):
            if folder.is_dir() and (folder / "solution.json").exists():
                folders.append(folder.name)
        return folders

    def _judge_solution(self, folder_name: str) -> None:
        """Judge a single solution."""
        folder = self.solutions_dir / folder_name
        logger.info("Judging %s", folder_name)

        try:
            issue = self._load_issue(folder)
            solution = self._load_solution(folder)
            judgment = self.judge.judge(issue, solution, folder_name)
            path = self.storage.save(judgment)
            logger.info(
                "Saved judgment to %s (overall: %.2f)",
                path.name,
                judgment.overall_score,
            )
        except Exception as e:
            logger.exception("Failed to judge %s: %s", folder_name, e)

    def _load_issue(self, folder: Path) -> Issue:
        """Load issue from a solution folder."""
        with open(folder / "issue.json", encoding="utf-8") as f:
            data = json.load(f)
        return Issue(**data)

    def _load_solution(self, folder: Path) -> Solution:
        """Load solution from a solution folder."""
        with open(folder / "solution.json", encoding="utf-8") as f:
            data = json.load(f)
        return Solution(**data)
