"""Publish generated solutions as anonymous PRs on the survey repository.

One PR per solution. Each PR gets a random short code; the code-to-model
mapping is written to a local gitignored file and never appears in the
survey repository. Creation order is shuffled so PR numbers do not cluster
by model. Safe to re-run: solutions already in the mapping are skipped.

Usage:
    python scripts/publish_survey_prs.py [--limit N]
"""

import argparse
import json
import random
import string
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOLUTIONS_DIR = ROOT / "data" / "solutions"
TIMES_PATH = ROOT / "data" / "exports" / "estimated_completion_times.json"
DEFAULT_MAPPING = ROOT / "data" / "exports" / "routing_test_pr_mapping.json"
DEFAULT_REPO = Path.home() / "Projects" / "Routing-Test"
CODE_ALPHABET = "".join(
    c for c in string.ascii_uppercase + string.digits if c not in "O0I1L"
)
CODE_LENGTH = 5
SLEEP_BETWEEN = 3

# Runtime artifacts in pre-cleanup patches that must not reach the survey repo.
APPLY_EXCLUDES = (
    "*/__pycache__/*",
    "*.pyc",
    "*/.venv/*",
    "*/venv/*",
    "*/node_modules/*",
    "*/.pytest_cache/*",
    "*.db",
    "*.sqlite3",
    "*.log",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
)


def run(cmd, cwd, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def load_mapping(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_mapping(path: Path, mapping: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def estimated_times() -> dict[str, int]:
    data = json.loads(TIMES_PATH.read_text(encoding="utf-8"))
    return {e["solution_id"]: e["estimated_seconds"] for e in data["solutions"]}


def new_code(used: set[str]) -> str:
    while True:
        code = "".join(random.choices(CODE_ALPHABET, k=CODE_LENGTH))
        if code not in used:
            return code


def solution_summary(run_dir: Path) -> str:
    try:
        info = json.loads((run_dir / "info.json").read_text(encoding="utf-8"))
        return (info.get("summary") or "").strip()
    except (OSError, json.JSONDecodeError):
        return ""


def pr_body(code: str, issue_number: int, summary: str, seconds: int | None) -> str:
    parts = []
    if summary:
        parts.append(f"### Agent-Generated Summary\n\n{summary}")
    if seconds is not None:
        parts.append(f"**Completion time: ~{seconds} seconds**")
    parts.append(f"This pull request is solution `{code}` for issue #{issue_number}.")
    return "\n\n---\n\n".join(parts) + "\n"


def publish_solution(
    repo: Path, task_id: str, run_dir: Path, code: str, seconds: int | None
) -> dict:
    issue_number = int(task_id.split("-")[0])
    branch = f"task-{issue_number:03d}/sol-{code}"
    patch = run_dir / "patch.diff"
    body = pr_body(code, issue_number, solution_summary(run_dir), seconds)

    run(["git", "checkout", "-q", "main"], repo)
    run(["git", "branch", "-D", branch], repo, check=False)
    run(["git", "checkout", "-q", "-b", branch], repo)
    try:
        excludes = [f"--exclude={pattern}" for pattern in APPLY_EXCLUDES]
        run(["git", "apply", "--directory", task_id, *excludes, str(patch)], repo)
        run(["git", "add", "-A"], repo)
        run(["git", "commit", "-q", "-m", f"Add solution {code}"], repo)
        run(["git", "push", "-q", "-u", "origin", branch], repo)
        pr_url = run(
            [
                "gh", "pr", "create",
                "--title", f"[{issue_number:03d}] Solution {code}",
                "--body", body,
                "--head", branch,
            ],
            repo,
        )
    finally:
        run(["git", "checkout", "-q", "main"], repo)
    return {"branch": branch, "pr_url": pr_url, "pr_number": int(pr_url.rsplit("/", 1)[-1])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--repo-path", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument(
        "--only",
        type=Path,
        default=None,
        help="JSON list of solution paths to publish; others are skipped",
    )
    args = parser.parse_args()

    only = None
    if args.only:
        only = set(json.loads(args.only.read_text(encoding="utf-8")))
    times = estimated_times()
    mapping = load_mapping(args.mapping)
    done = {entry["solution_path"] for entry in mapping}
    used_codes = {entry["code"] for entry in mapping}

    runs = []
    for run_dir in SOLUTIONS_DIR.glob("0*/openrouter_*/2*"):
        rel = run_dir.relative_to(SOLUTIONS_DIR).as_posix()
        if rel in done:
            continue
        if only is not None and rel not in only:
            continue
        if not (run_dir / "patch.diff").exists():
            print(f"SKIP (no patch): {rel}")
            continue
        runs.append((rel, run_dir))
    random.shuffle(runs)
    if args.limit:
        runs = runs[: args.limit]
    print(f"{len(runs)} solutions to publish ({len(done)} already done)")

    for i, (rel, run_dir) in enumerate(runs, 1):
        task_id, model_slug, run_id = rel.split("/")
        code = new_code(used_codes)
        seconds = times.get(f"{model_slug}__{run_id}")
        try:
            result = publish_solution(args.repo_path, task_id, run_dir, code, seconds)
        except RuntimeError as e:
            print(f"[{i}/{len(runs)}] FAILED {rel}: {e}")
            time.sleep(30)
            continue
        used_codes.add(code)
        mapping.append(
            {
                "code": code,
                "task_id": task_id,
                "issue_number": int(task_id.split("-")[0]),
                "model_slug": model_slug,
                "run_id": run_id,
                "solution_path": rel,
                **result,
            }
        )
        save_mapping(args.mapping, mapping)
        print(f"[{i}/{len(runs)}] {task_id} -> {code} ({result['pr_url']})")
        time.sleep(SLEEP_BETWEEN)

    print(f"Done. Mapping: {args.mapping} ({len(mapping)} entries)")


if __name__ == "__main__":
    main()
