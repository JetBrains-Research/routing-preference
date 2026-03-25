"""Solution storage and retrieval."""

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .models import Solution


class SolutionStorage:
    """Stores and retrieves solutions from disk.

    Structure:
        data/solutions/
          YYYYMMDD_HHMMSS_{issue_id}_{model}/
            solution.json
            patch.diff
    """

    def __init__(self, base_path: Path):
        """Initialize storage.

        Args:
            base_path: Base directory for solutions
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, solution: Solution) -> Path:
        """Save a solution to its own folder and return the folder path.

        Creates:
            solution.json - Full solution data with trajectory
            patch.diff - Git diff of the solution
        """
        folder_name = self._make_folder_name(solution)
        folder_path = self.base_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        # Save solution.json
        json_path = folder_path / "solution.json"
        temp_path = json_path.with_name(f"{json_path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(asdict(solution), f, indent=2, ensure_ascii=False)
        temp_path.replace(json_path)

        # Save patch.diff separately for easy access
        if solution.diff:
            diff_path = folder_path / "patch.diff"
            with open(diff_path, "w", encoding="utf-8") as f:
                f.write(solution.diff)

        return folder_path

    def load(self, path: Path) -> Solution:
        """Load a solution from a folder or file path."""
        if path.is_dir():
            path = path / "solution.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Solution(**data)

    def load_all(self) -> list[Solution]:
        """Load all solutions from the storage directory."""
        solutions = []
        for folder in sorted(self.base_path.iterdir()):
            if folder.is_dir():
                solution_file = folder / "solution.json"
                if solution_file.exists():
                    solutions.append(self.load(solution_file))
        return solutions

    def _sanitize(self, value: str) -> str:
        """Sanitize a string for use in a filename."""
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    def _make_folder_name(self, solution: Solution) -> str:
        """Generate a folder name for a solution (timestamp first for sorting)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = self._sanitize(solution.issue_id)
        safe_model = self._sanitize(solution.model)
        return f"{timestamp}_{safe_id}_{safe_model}"
