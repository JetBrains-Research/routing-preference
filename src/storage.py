"""Solution storage and retrieval."""

import json
from dataclasses import asdict
from pathlib import Path

from .models import Solution


class SolutionStorage:
    """Stores and retrieves solutions from disk."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, solution: Solution) -> Path:
        """Save a solution to disk and return the file path."""
        filename = self._make_filename(solution)
        path = self.base_path / filename
        with open(path, "w") as f:
            json.dump(asdict(solution), f, indent=2)
        return path

    def load(self, path: Path) -> Solution:
        """Load a solution from a file path."""
        with open(path) as f:
            data = json.load(f)
        return Solution(**data)

    def load_all(self) -> list[Solution]:
        """Load all solutions from the storage directory."""
        solutions = []
        for path in self.base_path.glob("*.json"):
            solutions.append(self.load(path))
        return solutions

    def _make_filename(self, solution: Solution) -> str:
        """Generate a filename for a solution."""
        safe_id = solution.issue_id.replace("/", "_").replace("#", "_")
        return f"{safe_id}_{solution.model}_{solution.provider}.json"
