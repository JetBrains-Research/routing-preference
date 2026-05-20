"""Solution storage and retrieval."""

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .models import Issue, Solution, SolutionInfo


class SolutionStorage:
    """
    Structure:
        data/solutions/
          {issue_id}/
            {model_slug}/
              {run_id}/
                issue.json
                solution.json
                info.json
                patch.diff
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        solution: Solution,
        issue: Issue,
        info: SolutionInfo,
    ) -> Path:
        """
        Creates:
            issue.json
            solution.json - Trajectory
            info.json - Summary, objective metrics, and exposure lists
            patch.diff - Git diff of the solution
        """
        folder_path = self._make_folder_path(solution)
        folder_path.mkdir(parents=True, exist_ok=True)

        issue_path = folder_path / "issue.json"
        self._atomic_write(
            issue_path, json.dumps(asdict(issue), indent=2, ensure_ascii=False)
        )

        solution_path = folder_path / "solution.json"
        solution_data = asdict(solution)
        self._atomic_write(
            solution_path, json.dumps(solution_data, indent=2, ensure_ascii=False)
        )

        info_path = folder_path / "info.json"
        self._atomic_write(
            info_path,
            json.dumps(asdict(info), indent=2, ensure_ascii=False),
        )

        if solution.diff:
            diff_path = folder_path / "patch.diff"
            self._atomic_write(diff_path, solution.diff)

        return folder_path

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to a file atomically"""
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_path.replace(path)

    @staticmethod
    def _sanitize(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    def _make_folder_path(self, solution: Solution) -> Path:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_id = self._sanitize(solution.issue_id)
        safe_model = self._sanitize(solution.model)
        return self.base_path / safe_id / safe_model / run_id


def iter_solution_paths(
    solutions_dir: Path,
    issue_id: str | None = None,
) -> list[Path]:
    """Return solution run directories under the issue/model/run tree."""
    root = solutions_dir / issue_id if issue_id else solutions_dir
    if not root.exists():
        return []
    return sorted(path.parent for path in root.rglob("solution.json"))


def solution_id_from_run_dir(run_dir: Path) -> str:
    """Return the stable solution id for an issue/model/run directory."""
    if run_dir.name == "solution.json":
        raise ValueError(
            "solution_id_from_run_dir expects a run directory, not solution.json"
        )
    return f"{run_dir.parent.name}__{run_dir.name}"


def solution_id_from_path(solution_path: Path) -> str:
    """Compatibility wrapper for run-directory inputs.

    Prefer solution_id_from_run_dir() in new code.
    """
    return solution_id_from_run_dir(solution_path)
