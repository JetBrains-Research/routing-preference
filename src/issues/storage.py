"""Storage for collected issues."""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from .models import CollectedIssue, Complexity, IssueType, TypeSource

logger = logging.getLogger(__name__)


class IssueStorage:
    """Stores and loads issues from JSON files."""

    def __init__(self, base_path: Path):
        """Initialize storage.

        Args:
            base_path: Directory to store issue files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _issue_to_dict(self, issue: CollectedIssue) -> dict:
        """Convert issue to dictionary for JSON serialization."""
        data = asdict(issue)
        # Convert enums to strings
        data["issue_type"] = issue.issue_type.value
        data["issue_type_source"] = issue.issue_type_source.value
        data["complexity"] = issue.complexity.value
        return data

    def _dict_to_issue(self, data: dict) -> CollectedIssue:
        """Convert dictionary back to CollectedIssue."""
        # Convert strings back to enums
        data["issue_type"] = IssueType(data.get("issue_type", "other"))
        data["issue_type_source"] = TypeSource(data.get("issue_type_source", "unknown"))
        data["complexity"] = Complexity(data.get("complexity", "unknown"))
        return CollectedIssue(**data)

    def save(self, issue: CollectedIssue) -> Path:
        """Save a single issue to a JSON file.

        Args:
            issue: The issue to save.

        Returns:
            Path to the saved file.
        """
        file_path = self.base_path / f"{issue.id}.json"
        data = self._issue_to_dict(issue)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path

    def save_batch(self, issues: list[CollectedIssue], filename: str = "issues.json") -> Path:
        """Save multiple issues to a single JSON file.

        Args:
            issues: List of issues to save.
            filename: Name of the output file.

        Returns:
            Path to the saved file.
        """
        file_path = self.base_path / filename
        data = [self._issue_to_dict(issue) for issue in issues]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Saved %d issues to %s", len(issues), file_path)
        return file_path

    def load(self, issue_id: str) -> CollectedIssue | None:
        """Load a single issue by ID.

        Args:
            issue_id: The issue ID to load.

        Returns:
            The loaded issue or None if not found.
        """
        file_path = self.base_path / f"{issue_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_issue(data)

    def load_batch(self, filename: str = "issues.json") -> list[CollectedIssue]:
        """Load multiple issues from a JSON file.

        Args:
            filename: Name of the file to load.

        Returns:
            List of loaded issues.
        """
        file_path = self.base_path / filename
        if not file_path.exists():
            return []

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        return [self._dict_to_issue(item) for item in data]

    def load_all(self) -> Iterator[CollectedIssue]:
        """Load all individual issue files from storage.

        Yields:
            CollectedIssue objects.
        """
        for file_path in sorted(self.base_path.glob("*.json")):
            if file_path.name == "issues.json":
                continue  # Skip batch file
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                yield self._dict_to_issue(data)
            except (json.JSONDecodeError, TypeError, KeyError, ValueError) as e:
                logger.warning("Failed to load %s: %s", file_path, e)

    def exists(self, issue_id: str) -> bool:
        """Check if an issue exists in storage.

        Args:
            issue_id: The issue ID to check.

        Returns:
            True if the issue exists.
        """
        file_path = self.base_path / f"{issue_id}.json"
        return file_path.exists()

    def count(self) -> int:
        """Count the number of stored issues.

        Returns:
            Number of issue files (excludes batch file).
        """
        return sum(1 for f in self.base_path.glob("*.json") if f.name != "issues.json")

    def delete(self, issue_id: str) -> bool:
        """Delete an issue from storage.

        Args:
            issue_id: The issue ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        file_path = self.base_path / f"{issue_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False


class HuggingFaceStorage:
    """Export issues to HuggingFace datasets format."""

    def __init__(self, dataset_name: str):
        """Initialize HuggingFace storage.

        Args:
            dataset_name: Name for the dataset (e.g., "org/routing-issues").
        """
        self.dataset_name = dataset_name

    def export(
        self,
        issues: list[CollectedIssue],
        push_to_hub: bool = False,
        token: str | None = None,
    ) -> Path:
        """Export issues to HuggingFace dataset format.

        Args:
            issues: List of issues to export.
            push_to_hub: Whether to push to HuggingFace Hub.
            token: HuggingFace token (uses HF_TOKEN env var if not provided).

        Returns:
            Path to the local dataset directory.
        """
        from datasets import Dataset

        # Convert to list of dicts
        records = []
        for issue in issues:
            record = {
                "id": issue.id,
                "repo": issue.repo,
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "labels": issue.labels,
                "state": issue.state,
                "created_at": issue.created_at,
                "author": issue.author,
                "author_association": issue.author_association,
                "comments_count": issue.comments_count,
                "reactions_count": issue.reactions_count,
                "html_url": issue.html_url,
                "issue_type": issue.issue_type.value,
                "complexity": issue.complexity.value,
                "base_commit": issue.base_commit,
                "assigned_reviewer": issue.assigned_reviewer,
            }
            records.append(record)

        dataset = Dataset.from_list(records)

        # Save locally
        local_path = Path(f"data/datasets/{self.dataset_name.replace('/', '_')}")
        local_path.mkdir(parents=True, exist_ok=True)
        dataset.save_to_disk(str(local_path))
        logger.info("Saved dataset to %s", local_path)

        # Push to Hub if requested
        if push_to_hub:
            dataset.push_to_hub(self.dataset_name, token=token)
            logger.info("Pushed dataset to %s", self.dataset_name)

        return local_path
