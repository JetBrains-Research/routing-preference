"""Load issues from HF datasets or local JSON."""

import json
from collections.abc import Iterator
from pathlib import Path

from datasets import load_dataset

from ..models import Issue


def load_issues(source: str, split: str = "test") -> "IssueDataset":
    """Load issues from HF or JSON

    Args:
        source: HF dataset name or path to local JSON
        split: Dataset split
    """
    path = Path(source)
    if path.suffix == ".json":
        return LocalIssueDataset(source)
    return HuggingFaceIssueDataset(source, split)


class IssueDataset:
    """Base class for issue datasets."""

    def __len__(self) -> int:
        raise NotImplementedError

    def __getitem__(self, idx: int) -> Issue:
        raise NotImplementedError

    def __iter__(self) -> Iterator[Issue]:
        for i in range(len(self)):
            yield self[i]


class HuggingFaceIssueDataset(IssueDataset):
    def __init__(self, dataset_name: str, split: str = "test"):
        self.dataset_name = dataset_name
        self.split = split
        self._dataset = load_dataset(dataset_name, split=split)

    def __len__(self) -> int:
        return len(self._dataset)

    def __getitem__(self, idx: int) -> Issue:
        row = self._dataset[idx]
        return _row_to_issue(row)


class LocalIssueDataset(IssueDataset):
    """Load issues from a local JSON.

    List of objects. Each one should have id, title, body. GitHub issues also
    carry repo and number; zero-shot prompts omit them.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        with self.path.open(encoding="utf-8") as f:
            self._issues = json.load(f)

    def __len__(self) -> int:
        return len(self._issues)

    def __getitem__(self, idx: int) -> Issue:
        row = self._issues[idx]
        return _row_to_issue(row, base_dir=self.path.parent)


def _row_to_issue(row: dict, base_dir: Path | None = None) -> Issue:
    return Issue(
        # Required
        issue_id=str(row["id"]),
        title=row["title"],
        body=row["body"],
        # GitHub fields, absent for zero-shot prompts
        repo=row.get("repo"),
        number=row.get("number"),
        task_type=row.get("task_type"),
        assets_dir=_resolve_assets_dir(row.get("assets_dir"), base_dir),
        # Optional
        labels=row.get("labels") or [],
        base_commit=str(bc) if (bc := row.get("base_commit")) else None,
        issue_type=row.get("issue_type"),
        complexity=row.get("complexity"),
        created_at=row.get("created_at"),
        author=row.get("author"),
        html_url=row.get("html_url"),
        state=row.get("state"),
        comments_count=row.get("comments_count"),
        reactions_count=row.get("reactions_count"),
    )


def _resolve_assets_dir(value: str | None, base_dir: Path | None) -> str | None:
    """Resolve an assets path relative to the dataset file that declared it."""
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return str(path)
