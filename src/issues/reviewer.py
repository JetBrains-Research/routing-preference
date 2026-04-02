"""Reviewer tracking and assignment."""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from .models import CollectedIssue, Reviewer

logger = logging.getLogger(__name__)


class ReviewerManager:
    """Manages reviewer information and assignments."""

    def __init__(self, storage_path: Path):
        """Initialize the reviewer manager.

        Args:
            storage_path: Path to store reviewer data.
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.reviewers_file = self.storage_path / "reviewers.json"
        self._reviewers: dict[str, Reviewer] = {}
        self._load()

    def _load(self) -> None:
        """Load reviewers from storage."""
        if self.reviewers_file.exists():
            with open(self.reviewers_file, encoding="utf-8") as f:
                data = json.load(f)
            self._reviewers = {
                username: Reviewer(**rev_data)
                for username, rev_data in data.items()
            }
            logger.info("Loaded %d reviewers", len(self._reviewers))

    def _save(self) -> None:
        """Save reviewers to storage."""
        data = {
            username: asdict(reviewer)
            for username, reviewer in self._reviewers.items()
        }
        with open(self.reviewers_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_reviewer(self, reviewer: Reviewer) -> None:
        """Add or update a reviewer.

        Args:
            reviewer: The reviewer to add.
        """
        self._reviewers[reviewer.github_username] = reviewer
        self._save()
        logger.info("Added reviewer: %s", reviewer.github_username)

    def get_reviewer(self, username: str) -> Reviewer | None:
        """Get a reviewer by username.

        Args:
            username: GitHub username.

        Returns:
            Reviewer or None if not found.
        """
        return self._reviewers.get(username)

    def get_reviewers_for_repo(self, repo: str) -> list[Reviewer]:
        """Get all reviewers for a repository.

        Args:
            repo: Repository full name (owner/name).

        Returns:
            List of reviewers for this repo.
        """
        return [
            reviewer for reviewer in self._reviewers.values()
            if repo in reviewer.repos
        ]

    def get_available_reviewer(self, repo: str) -> Reviewer | None:
        """Get an available reviewer for a repository.

        Args:
            repo: Repository full name.

        Returns:
            A reviewer with available capacity, or None.
        """
        reviewers = self.get_reviewers_for_repo(repo)

        # Sort by available capacity (highest first)
        reviewers.sort(key=lambda r: r.available_capacity, reverse=True)

        for reviewer in reviewers:
            if reviewer.available_capacity > 0 and reviewer.consent_given:
                return reviewer

        return None

    def assign_reviewer(
        self,
        issue: CollectedIssue,
        reviewer: Reviewer | None = None,
    ) -> CollectedIssue:
        """Assign a reviewer to an issue.

        Priority:
        1. Specific reviewer if provided
        2. Available maintainer from the repository
        3. Issue author as fallback

        Args:
            issue: The issue to assign.
            reviewer: Specific reviewer, or None to auto-select.

        Returns:
            Updated issue with assigned_reviewer and reviewer_type set.
        """
        reviewer_type = "maintainer"

        if reviewer is None:
            reviewer = self.get_available_reviewer(issue.repo)

        # Fallback to issue author if no maintainer available
        if reviewer is None and issue.author:
            issue.assigned_reviewer = issue.author
            issue.reviewer_type = "author"
            logger.info(
                "Assigned %s to author %s (no maintainer available)",
                issue.id,
                issue.author,
            )
            return issue

        if reviewer is None:
            logger.warning(
                "No available reviewer for %s (repo: %s, no author either)",
                issue.id,
                issue.repo,
            )
            return issue

        # Update reviewer's assignments
        reviewer.assigned_issues.append(issue.id)
        self._save()

        # Update issue
        issue.assigned_reviewer = reviewer.github_username
        issue.reviewer_type = reviewer_type

        logger.info(
            "Assigned %s to %s %s",
            issue.id,
            reviewer_type,
            reviewer.github_username,
        )

        return issue

    def bulk_assign(
        self,
        issues: list[CollectedIssue],
    ) -> tuple[list[CollectedIssue], list[CollectedIssue]]:
        """Assign reviewers to multiple issues.

        Args:
            issues: List of issues to assign.

        Returns:
            Tuple of (assigned_issues, unassigned_issues).
        """
        assigned = []
        unassigned = []

        for issue in issues:
            issue = self.assign_reviewer(issue)
            if issue.assigned_reviewer:
                assigned.append(issue)
            else:
                unassigned.append(issue)

        logger.info(
            "Bulk assignment: %d assigned, %d unassigned",
            len(assigned),
            len(unassigned),
        )

        return assigned, unassigned

    def import_maintainers(
        self,
        repo: str,
        maintainers: list[str],
        max_reviews_per_maintainer: int = 10,
    ) -> None:
        """Import maintainers as potential reviewers.

        Args:
            repo: Repository full name.
            maintainers: List of GitHub usernames.
            max_reviews_per_maintainer: Max reviews each can handle.
        """
        for username in maintainers:
            if username in self._reviewers:
                # Add repo to existing reviewer
                if repo not in self._reviewers[username].repos:
                    self._reviewers[username].repos.append(repo)
            else:
                # Create new reviewer
                reviewer = Reviewer(
                    github_username=username,
                    repos=[repo],
                    consent_given=False,  # Needs explicit consent
                    max_reviews=max_reviews_per_maintainer,
                )
                self._reviewers[username] = reviewer

        self._save()
        logger.info(
            "Imported %d maintainers for %s",
            len(maintainers),
            repo,
        )

    def set_consent(self, username: str, consent: bool) -> bool:
        """Set reviewer consent status.

        Args:
            username: GitHub username.
            consent: Whether they consented.

        Returns:
            True if reviewer was found and updated.
        """
        if username not in self._reviewers:
            return False

        self._reviewers[username].consent_given = consent
        self._save()
        logger.info(
            "Set consent for %s: %s",
            username,
            "granted" if consent else "revoked",
        )
        return True

    def get_stats(self) -> dict:
        """Get reviewer statistics.

        Returns:
            Dictionary with stats.
        """
        total = len(self._reviewers)
        with_consent = sum(1 for r in self._reviewers.values() if r.consent_given)
        total_capacity = sum(r.max_reviews for r in self._reviewers.values())
        total_assigned = sum(len(r.assigned_issues) for r in self._reviewers.values())

        return {
            "total_reviewers": total,
            "with_consent": with_consent,
            "total_capacity": total_capacity,
            "total_assigned": total_assigned,
            "available_capacity": total_capacity - total_assigned,
        }

    def list_reviewers(self) -> list[Reviewer]:
        """Get all reviewers.

        Returns:
            List of all reviewers.
        """
        return list(self._reviewers.values())
