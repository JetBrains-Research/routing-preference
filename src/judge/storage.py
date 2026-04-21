"""Storage for judgments."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import Judgment, Score


def judgment_filename(
    exposure: str,
    basis: str,
    granularity: str,
    characteristic_id: str | None,
) -> str:
    """Build the filename for a judgment variant.

    Format: {exposure}_{basis}_{all|characteristic}.json
    """
    suffix = characteristic_id if granularity == "single" else "all"
    return f"{exposure}_{basis}_{suffix}.json"


class JudgmentStorage:
    def __init__(self, solutions_dir: Path):
        self.solutions_dir = solutions_dir

    def save(self, judgment: Judgment) -> Path:
        """Save a judgment to the solution's judgments/ folder."""
        folder = self.solutions_dir / judgment.solution_folder
        if not folder.exists():
            raise ValueError(f"Solution folder not found: {folder}")

        judgments_dir = folder / "judgments"
        judgments_dir.mkdir(exist_ok=True)

        filename = judgment_filename(
            judgment.exposure,
            judgment.basis,
            judgment.granularity,
            judgment.characteristic_id,
        )
        path = judgments_dir / filename
        self._atomic_write(
            path, json.dumps(asdict(judgment), indent=2, ensure_ascii=False)
        )
        return path

    def load(
        self,
        solution_folder: str,
        exposure: str,
        basis: str,
        granularity: str,
        characteristic_id: str | None = None,
    ) -> Judgment | None:
        """Load a specific judgment variant."""
        filename = judgment_filename(exposure, basis, granularity, characteristic_id)
        path = self.solutions_dir / solution_folder / "judgments" / filename
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["scores"] = [Score(**s) for s in data["scores"]]
        if data.get("score_scale"):
            data["score_scale"] = tuple(data["score_scale"])
        return Judgment(**data)

    def has_judgment(
        self,
        folder: Path,
        exposure: str,
        basis: str,
        granularity: str,
        characteristic_id: str | None = None,
    ) -> bool:
        if not folder.is_dir() or not (folder / "solution.json").exists():
            return False
        filename = judgment_filename(exposure, basis, granularity, characteristic_id)
        return (folder / "judgments" / filename).exists()

    def list_unjudged(
        self,
        exposure: str,
        basis: str,
        granularity: str,
        characteristic_id: str | None = None,
    ) -> list[str]:
        return [
            folder.name
            for folder in sorted(self.solutions_dir.iterdir())
            if folder.is_dir()
            and (folder / "solution.json").exists()
            and not self.has_judgment(
                folder, exposure, basis, granularity, characteristic_id
            )
        ]

    def _atomic_write(self, path: Path, content: str) -> None:
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_path.replace(path)
