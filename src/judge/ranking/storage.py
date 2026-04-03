"""Storage for comparative rankings."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import ComparativeJudgment, Ranking


class RankingStorage:
    """Stores comparative rankings per issue.

    Structure:
        data/rankings/
          {issue_id}.json
    """

    def __init__(self, rankings_dir: Path):
        self.rankings_dir = rankings_dir
        self.rankings_dir.mkdir(parents=True, exist_ok=True)

    def save(self, judgment: ComparativeJudgment) -> Path:
        """Save a comparative judgment."""
        path = self.rankings_dir / f"{judgment.issue_id}.json"
        self._atomic_write(
            path, json.dumps(asdict(judgment), indent=2, ensure_ascii=False)
        )
        return path

    def load(self, issue_id: str) -> ComparativeJudgment | None:
        """Load a comparative judgment for an issue."""
        path = self.rankings_dir / f"{issue_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Convert rankings dicts back to Ranking objects
        data["rankings"] = [Ranking(**r) for r in data["rankings"]]
        return ComparativeJudgment(**data)

    def has_ranking(self, issue_id: str) -> bool:
        """Check if an issue has a comparative ranking."""
        path = self.rankings_dir / f"{issue_id}.json"
        return path.exists()

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to a file atomically."""
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        temp_path.replace(path)
