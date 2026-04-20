"""Fetch source files from GitHub for V2 scoring."""

import os
import re

import requests


def extract_changed_files(diff: str) -> list[str]:
    """Extract original file paths from a git diff.

    Skips newly created files (those with --- /dev/null) since they
    don't exist at the base commit.
    """
    paths = []
    seen = set()
    for match in re.finditer(r"^--- (?:a/)?(.+)$", diff, re.MULTILINE):
        path = match.group(1).strip()
        if path == "/dev/null":
            continue
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def fetch_source_files(
    repo: str,
    base_commit: str,
    paths: list[str],
    timeout: int = 30,
) -> dict[str, str]:
    """Fetch original source files from GitHub at a specific commit.

    Args:
        repo: "owner/name" format.
        base_commit: git SHA to fetch files from.
        paths: list of file paths relative to repo root.
        timeout: per-request timeout in seconds.

    Returns:
        Dict of filepath -> file content. Missing/binary files are skipped.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    source_files = {}
    for path in paths:
        url = f"https://raw.githubusercontent.com/{repo}/{base_commit}/{path}"
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        try:
            source_files[path] = response.content.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return source_files
