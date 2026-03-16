"""Solution storage and retrieval."""

import json
import re
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

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
        # Atomic write: unique temp file avoids cross-process collisions
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(asdict(solution), f, indent=2, ensure_ascii=False)
        temp_path.replace(path)
        return path

    def load(self, path: Path) -> Solution:
        """Load a solution from a file path."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Solution(**data)

    def load_all(self) -> list[Solution]:
        """Load all solutions from the storage directory."""
        solutions = []
        for path in sorted(self.base_path.glob("*.json")):
            solutions.append(self.load(path))
        return solutions

    def _sanitize(self, value: str) -> str:
        """Sanitize a string for use in a filename."""
        return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

    def _make_filename(self, solution: Solution) -> str:
        """Generate a unique filename for a solution."""
        safe_id = self._sanitize(solution.issue_id)
        safe_model = self._sanitize(solution.model)
        safe_provider = self._sanitize(solution.provider)
        unique_suffix = uuid4().hex[:8]
        return f"{safe_id}_{safe_model}_{safe_provider}_{unique_suffix}.json"
