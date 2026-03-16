"""Issue collection from GitHub."""

import json
import subprocess

from .models import Issue


class IssueCollector:
    """Fetches issues from GitHub using the gh CLI."""

    def fetch(self, repo: str, issue_number: int) -> Issue:
        """Fetch a single issue from a repository."""
        result = subprocess.run(
            [
                "gh", "issue", "view", str(issue_number),
                "--repo", repo,
                "--json", "number,title,body,labels",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch issue: {result.stderr}")

        data = json.loads(result.stdout)
        return Issue(
            id=f"{repo}#{issue_number}",
            repo=repo,
            number=data["number"],
            title=data["title"],
            body=data["body"],
            labels=[label["name"] for label in data.get("labels", [])],
        )

    def fetch_batch(self, repo: str, limit: int = 10) -> list[Issue]:
        """Fetch multiple open issues from a repository."""
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--repo", repo,
                "--limit", str(limit),
                "--json", "number,title,body,labels",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch issues: {result.stderr}")

        issues = []
        for data in json.loads(result.stdout):
            issues.append(Issue(
                id=f"{repo}#{data['number']}",
                repo=repo,
                number=data["number"],
                title=data["title"],
                body=data["body"],
                labels=[label["name"] for label in data.get("labels", [])],
            ))
        return issues
