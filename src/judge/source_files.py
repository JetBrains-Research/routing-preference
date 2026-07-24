"""Fetch source files from GitHub for V2 scoring."""

import json
import logging
import os
import re
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MAX_ASSET_FILE_BYTES = 50_000
MAX_ASSET_TOTAL_BYTES = 150_000


def load_asset_files(
    assets_dir: str,
    max_file_bytes: int = MAX_ASSET_FILE_BYTES,
    max_total_bytes: int = MAX_ASSET_TOTAL_BYTES,
) -> dict[str, str]:
    """Load the starting files a zero-shot task provided to the agent.

    Returns paths relative to the workspace (including the assets folder
    name, matching how the agent saw them). Binary and oversized files are
    skipped with a log line; loading stops before the total budget is
    exceeded.
    """
    root = Path(assets_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Assets directory not found: {assets_dir}")

    asset_files: dict[str, str] = {}
    total = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = f"{root.name}/{path.relative_to(root).as_posix()}"
        size = path.stat().st_size
        if size > max_file_bytes:
            logger.info("Skipping oversized asset %s (%d bytes)", relative, size)
            continue
        if total + size > max_total_bytes:
            logger.info("Asset budget reached; skipping %s", relative)
            continue
        try:
            asset_files[relative] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.info("Skipping binary asset %s", relative)
            continue
        total += size
    return asset_files


def load_exposed_files(solution_folder: Path) -> list[str]:
    """Load the list of files exposed to the agent during solution generation."""
    path = solution_folder / "info.json"
    if not path.exists():
        raise FileNotFoundError(
            f"info.json not found in {solution_folder}. "
            "Was this solution generated with the patched mini-swe-agent?"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("exposed_files", [])


def extract_changed_files(diff: str) -> list[str]:
    """Extract original file paths from a git diff.

    Skips newly created files because they do not exist at the base commit.
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
        if _should_skip_path(path):
            continue
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


def _should_skip_path(path: str) -> bool:
    if not path or path.endswith("/"):
        return True
    parts = path.split("/")
    return any(part in {"", ".", ".."} for part in parts)
