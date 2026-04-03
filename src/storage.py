"""Solution storage and retrieval."""

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .models import Issue, Solution


class SolutionStorage:
    """
    Structure:
        data/solutions/
          YYYYMMDD_HHMMSS_{issue_id}_{model}/
            solution.json
            patch.diff
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, solution: Solution, issue: Issue) -> Path:
        """
        Creates:
            issue.json
            solution.json - Trajectory
            patch.diff - Git diff of the solution
        """
        folder_name = self._make_folder_name(solution)
        folder_path = self.base_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        issue_path = folder_path / "issue.json"
        self._atomic_write(
            issue_path, json.dumps(asdict(issue), indent=2, ensure_ascii=False)
        )

        solution_path = folder_path / "solution.json"
        self._atomic_write(
            solution_path, json.dumps(asdict(solution), indent=2, ensure_ascii=False)
        )

        if solution.diff:
            diff_path = folder_path / "patch.diff"
            self._atomic_write(diff_path, solution.diff)

        return folder_path

    def load(self, path: Path) -> Solution:
        """Load a solution"""
        if path.is_dir():
            path = path / "solution.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Solution(**data)

    def load_all(self) -> list[Solution]:
        """Load all solutions from the storage directory"""
        solutions = []
        for folder in sorted(self.base_path.iterdir()):
            if folder.is_dir():
                solution_file = folder / "solution.json"
                if solution_file.exists():
                    solutions.append(self.load(solution_file))
        return solutions

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to a file atomically"""
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_path.replace(path)

    def _sanitize(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    def _make_folder_name(self, solution: Solution) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = self._sanitize(solution.issue_id)
        safe_model = self._sanitize(solution.model)
        return f"{timestamp}_{safe_id}_{safe_model}"
