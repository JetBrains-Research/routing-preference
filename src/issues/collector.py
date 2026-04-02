"""GitHub issue collector using the REST API."""

import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Iterator

import requests

from .models import CollectedIssue, Repository

logger = logging.getLogger(__name__)

DEFAULT_CUTOFF_DAYS = 730  # 2 years


class GitHubAPIError(Exception):
    """Error from GitHub API."""
    pass


class RateLimitError(GitHubAPIError):
    """Rate limit exceeded."""
    pass


class IssueCollector:
    """Collects issues from GitHub repositories."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        cutoff_days: int = DEFAULT_CUTOFF_DAYS,
    ):
        """Initialize the collector.

        Args:
            token: GitHub personal access token. If None, tries to get from
                   GITHUB_TOKEN env var or `gh auth token`.
            cutoff_days: Only collect issues created within this many days.
        """
        self.token = token or self._get_token()
        self.cutoff_date = datetime.now() - timedelta(days=cutoff_days)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get_token(self) -> str | None:
        """Get GitHub token from environment or gh CLI."""
        # Try environment variable first
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            return token

        # Try gh CLI
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("No GitHub token found. API rate limits will be strict.")
            return None

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        retry_on_rate_limit: bool = True,
    ) -> dict | list:
        """Make a request to the GitHub API."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.request(method, url, params=params)
        except requests.RequestException as e:
            raise GitHubAPIError(f"Request failed: {e}") from e

        # Handle rate limiting
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining == "0" and retry_on_rate_limit:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_seconds = max(0, reset_time - time.time()) + 1
                logger.warning(
                    "Rate limit exceeded. Waiting %.0f seconds...",
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                return self._request(method, endpoint, params, retry_on_rate_limit=False)
            # Check if it's actually a rate limit issue
            if remaining == "0":
                raise RateLimitError("GitHub API rate limit exceeded")
            # Otherwise it's a forbidden error (no permission)
            raise GitHubAPIError(f"Forbidden: {endpoint} - {response.text[:200]}")

        if response.status_code == 404:
            raise GitHubAPIError(f"Not found: {endpoint}")

        if not response.ok:
            raise GitHubAPIError(
                f"API error {response.status_code}: {response.text[:200]}"
            )

        try:
            return response.json()
        except requests.JSONDecodeError as e:
            raise GitHubAPIError(f"Invalid JSON response: {e}") from e

    def get_repository(self, owner: str, name: str) -> Repository:
        """Get repository metadata."""
        data = self._request("GET", f"/repos/{owner}/{name}")
        repo = Repository.from_github_repo(data)

        # Get recent commit to check activity
        try:
            commits = self._request(
                "GET",
                f"/repos/{owner}/{name}/commits",
                params={"per_page": 1},
            )
            if commits:
                repo.last_commit_date = commits[0].get("commit", {}).get(
                    "committer", {}
                ).get("date")
        except GitHubAPIError:
            pass

        return repo

    def get_maintainers(self, owner: str, name: str, limit: int = 5) -> list[str]:
        """Get top contributors (potential maintainers) for a repository."""
        try:
            contributors = self._request(
                "GET",
                f"/repos/{owner}/{name}/contributors",
                params={"per_page": limit},
            )
            return [c["login"] for c in contributors if c.get("login")]
        except GitHubAPIError as e:
            logger.warning("Failed to get contributors for %s/%s: %s", owner, name, e)
            return []

    def collect_issues(
        self,
        owner: str,
        name: str,
        state: str = "all",
        per_page: int = 100,
        max_issues: int | None = None,
    ) -> Iterator[CollectedIssue]:
        """Collect issues from a repository.

        Args:
            owner: Repository owner.
            name: Repository name.
            state: Issue state filter (open, closed, all).
            per_page: Number of issues per API request.
            max_issues: Maximum number of issues to collect.

        Yields:
            CollectedIssue objects.
        """
        repo_full = f"{owner}/{name}"
        page = 1
        collected = 0
        cutoff_iso = self.cutoff_date.isoformat()

        logger.info("Collecting issues from %s (since %s)", repo_full, cutoff_iso[:10])

        while True:
            params = {
                "state": state,
                "sort": "created",
                "direction": "desc",
                "per_page": per_page,
                "page": page,
                "since": cutoff_iso,
            }

            try:
                issues = self._request("GET", f"/repos/{owner}/{name}/issues", params)
            except GitHubAPIError as e:
                logger.error("Failed to fetch issues page %d: %s", page, e)
                break

            if not issues:
                break

            for issue_data in issues:
                # Skip pull requests (GitHub API returns PRs in issues endpoint)
                if "pull_request" in issue_data:
                    continue

                # Check cutoff date
                created_at = issue_data.get("created_at", "")
                if created_at and created_at < cutoff_iso:
                    logger.info("Reached cutoff date, stopping collection")
                    return

                issue = CollectedIssue.from_github_issue(repo_full, issue_data)
                yield issue

                collected += 1
                if max_issues and collected >= max_issues:
                    logger.info("Reached max_issues limit (%d)", max_issues)
                    return

            page += 1

            # Be nice to the API
            time.sleep(0.5)

        logger.info("Collected %d issues from %s", collected, repo_full)

    def get_commit_at_date(
        self,
        owner: str,
        name: str,
        target_date: str,
    ) -> str | None:
        """Get the commit SHA closest to (but before) a given date.

        Args:
            owner: Repository owner.
            name: Repository name.
            target_date: ISO format date string.

        Returns:
            Commit SHA or None if not found.
        """
        try:
            commits = self._request(
                "GET",
                f"/repos/{owner}/{name}/commits",
                params={"until": target_date, "per_page": 1},
            )
            if commits:
                return commits[0].get("sha")
        except GitHubAPIError as e:
            logger.warning(
                "Failed to get commit for %s/%s at %s: %s",
                owner, name, target_date, e,
            )
        return None

    def enrich_with_base_commit(self, issue: CollectedIssue) -> CollectedIssue:
        """Add base_commit to an issue based on its created_at date."""
        if issue.base_commit:
            return issue

        owner, name = issue.repo.split("/")
        commit = self.get_commit_at_date(owner, name, issue.created_at)

        if commit:
            issue.base_commit = commit
            logger.debug(
                "Found base commit %s for issue %s",
                commit[:8],
                issue.id,
            )

        return issue
