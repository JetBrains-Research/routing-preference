"""Storage for judgments."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import Judgment, Score


class JudgmentStorage:
    def __init__(self, solutions_dir: Path):
        self.solutions_dir = solutions_dir

    def save(self, judgment: Judgment) -> Path:
        """Save a judgment to the solution folder"""
        folder = self.solutions_dir / judgment.solution_folder
        if not folder.exists():
            raise ValueError(f"Solution folder not found: {folder}")

        path = folder / "judgment.json"
        self._atomic_write(
            path, json.dumps(asdict(judgment), indent=2, ensure_ascii=False)
        )
        return path

    def load(self, solution_folder: str) -> Judgment | None:
        """Load a judgment"""
        path = self.solutions_dir / solution_folder / "judgment.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["scores"] = [Score(**s) for s in data["scores"]]
        if data.get("score_scale"):
            data["score_scale"] = tuple(data["score_scale"])
        return Judgment(**data)

    def has_judgment(self, folder: Path) -> bool:
        return (
            folder.is_dir()
            and (folder / "solution.json").exists()
            and (folder / "judgment.json").exists()
        )

    def list_unjudged(self) -> list[str]:
        return [
            folder.name
            for folder in sorted(self.solutions_dir.iterdir())
            if not self.has_judgment(folder)
        ]

    def _atomic_write(self, path: Path, content: str) -> None:
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_path.replace(path)
