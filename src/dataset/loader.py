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

    List of objects and each one should have: issue_id, repo, number, title, body, assigned_reviewer, reviewer_type
    """

    def __init__(self, path: str):
        self.path = Path(path)
        with self.path.open(encoding="utf-8") as f:
            self._issues = json.load(f)

    def __len__(self) -> int:
        return len(self._issues)

    def __getitem__(self, idx: int) -> Issue:
        row = self._issues[idx]
        return _row_to_issue(row)


def _row_to_issue(row: dict) -> Issue:
    return Issue(
        # Required
        issue_id=str(row["id"]),
        repo=row["repo"],
        number=row["number"],
        title=row["title"],
        body=row["body"],
        assigned_reviewer=row.get("assigned_reviewer"),
        reviewer_type=row.get("reviewer_type"),
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
