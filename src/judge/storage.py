"""Storage for judgments."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import Judgment, Score


class JudgmentStorage:
    """Stores judgments alongside their solutions """

    def __init__(self, solutions_dir: Path):
        self.solutions_dir = solutions_dir

    def save(self, judgment: Judgment) -> Path:
        """Save a judgment to the solution folder."""
        folder = self.solutions_dir / judgment.solution_folder
        if not folder.exists():
            raise ValueError(f"Solution folder not found: {folder}")

        path = folder / "judgment.json"
        self._atomic_write(path, json.dumps(asdict(judgment), indent=2, ensure_ascii=False))
        return path

    def load(self, solution_folder: str) -> Judgment | None:
        """Load a judgment from a solution folder, if it exists."""
        path = self.solutions_dir / solution_folder / "judgment.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Convert scores dicts back to Score objects
        data["scores"] = [Score(**s) for s in data["scores"]]
        return Judgment(**data)

    def has_judgment(self, solution_folder: str) -> bool:
        """Check if a solution folder has a judgment."""
        path = self.solutions_dir / solution_folder / "judgment.json"
        return path.exists()

    def list_unjudged(self) -> list[str]:
        """List solution folders that don't have judgments yet."""
        unjudged = []
        for folder in sorted(self.solutions_dir.iterdir()):
            if folder.is_dir() and (folder / "solution.json").exists():
                if not (folder / "judgment.json").exists():
                    unjudged.append(folder.name)
        return unjudged

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to a file atomically using temp file + replace."""
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_path.replace(path)
