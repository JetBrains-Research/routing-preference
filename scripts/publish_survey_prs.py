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

SOLUTIONS_DIR = Path(__file__).parent.parent / "data" / "solutions"
MAPPING_PATH = (
    Path(__file__).parent.parent / "data" / "exports" / "routing_test_pr_mapping.json"
)
SURVEY_REPO = Path.home() / "Projects" / "Routing-Test"
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


def run(cmd, cwd=SURVEY_REPO, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def load_mapping() -> list[dict]:
    if MAPPING_PATH.exists():
        return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return []


def save_mapping(mapping: list[dict]) -> None:
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAPPING_PATH.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


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


def publish_solution(task_id: str, run_dir: Path, code: str) -> dict:
    issue_number = int(task_id.split("-")[0])
    branch = f"task-{issue_number:03d}/sol-{code}"
    patch = run_dir / "patch.diff"
    summary = solution_summary(run_dir)
    body = f"Solution `{code}` for task #{issue_number}."
    if summary:
        body = f"{summary}\n\n---\nSolution `{code}` for task #{issue_number}."

    run(["git", "checkout", "-q", "main"])
    run(["git", "branch", "-D", branch], check=False)
    run(["git", "checkout", "-q", "-b", branch])
    try:
        excludes = [f"--exclude={pattern}" for pattern in APPLY_EXCLUDES]
        run(["git", "apply", "--directory", task_id, *excludes, str(patch)])
        run(["git", "add", "-A"])
        run(["git", "commit", "-q", "-m", f"Add solution {code}"])
        run(["git", "push", "-q", "-u", "origin", branch])
        pr_url = run(
            [
                "gh", "pr", "create",
                "--title", f"[{issue_number:03d}] Solution {code}",
                "--body", body,
                "--head", branch,
            ]
        )
    finally:
        run(["git", "checkout", "-q", "main"])
    return {"branch": branch, "pr_url": pr_url, "pr_number": int(pr_url.rsplit("/", 1)[-1])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    mapping = load_mapping()
    done = {entry["solution_path"] for entry in mapping}
    used_codes = {entry["code"] for entry in mapping}

    runs = []
    for run_dir in SOLUTIONS_DIR.glob("0*/openrouter_*/2*"):
        rel = run_dir.relative_to(SOLUTIONS_DIR).as_posix()
        if rel in done:
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
        try:
            result = publish_solution(task_id, run_dir, code)
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
        save_mapping(mapping)
        print(f"[{i}/{len(runs)}] {task_id} -> {code} ({result['pr_url']})")
        time.sleep(SLEEP_BETWEEN)

    print(f"Done. Mapping: {MAPPING_PATH} ({len(mapping)} entries)")


if __name__ == "__main__":
    main()
