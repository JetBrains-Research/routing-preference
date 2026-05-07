"""Unified CLI for routing-preference."""

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"
DEFAULT_RANKINGS_DIR = PROJECT_ROOT / "data" / "rankings"
DEFAULT_SELECTIONS_DIR = PROJECT_ROOT / "data" / "selections"

CHARACTERISTICS = ["intent", "correctness", "scope", "quality"]
N_RANKING_SOLUTIONS = 7


def cmd_generate(args) -> None:
    """Generate solutions for issues."""
    from .dataset import load_issues
    from .pipeline import Pipeline

    models = args.models or ["openai/gpt-4o-mini"]

    logger.info("Loading dataset: %s (split: %s)", args.dataset, args.split)
    dataset = load_issues(args.dataset, split=args.split)
    logger.info("Found %d issues", len(dataset))
    logger.info("Models: %s", ", ".join(models))
    logger.info("Environment: %s", args.sandbox)

    pipeline = Pipeline(solutions_dir=args.output, environment_type=args.sandbox)
    pipeline.run(dataset=dataset, models=models, limit=args.limit)


def _load_issue(folder: Path):
    from .models import Issue

    with open(folder / "issue.json", encoding="utf-8") as f:
        data = json.load(f)
    if "id" in data and "issue_id" not in data:
        data["issue_id"] = data.pop("id")
    return Issue(**data)


def _load_solution(folder: Path):
    from .models import Solution

    with open(folder / "solution.json", encoding="utf-8") as f:
        return Solution(**json.load(f))


def _gather_source_files(exposure: str, folder: Path, issue, solution):
    """Gather source files for V2 exposures. Returns None for V1."""
    from .judge.source_files import (
        extract_changed_files,
        fetch_source_files,
        load_exposed_files,
    )

    if not exposure.startswith("V2"):
        return None
    if not issue.base_commit:
        raise ValueError(
            f"V2 requires base_commit on issue {issue.issue_id}"
        )
    if exposure == "V2.0":
        paths = extract_changed_files(solution.diff)
    else:
        paths = load_exposed_files(folder)
    return fetch_source_files(issue.repo, issue.base_commit, paths)


def cmd_judge(args) -> None:
    """Judge solutions — scoring or ranking based on --basis."""
    if args.granularity == "single" and not args.characteristic:
        raise ValueError("--characteristic is required when --granularity single")

    if args.basis == "scoring":
        _cmd_judge_scoring(args)
    else:
        _cmd_judge_ranking(args)


def _cmd_judge_scoring(args) -> None:
    from .judge import Judge, ScoringStorage

    judge = Judge(model=args.model, exposure=args.exposure)
    storage = ScoringStorage(args.solutions_dir)

    if args.solution:
        folders = [args.solution]
    elif args.force:
        folders = [
            f.name
            for f in sorted(args.solutions_dir.iterdir())
            if f.is_dir() and (f / "solution.json").exists()
        ]
    else:
        folders = storage.list_unjudged(
            exposure=args.exposure,
            basis=args.basis,
            granularity=args.granularity,
            characteristic_id=args.characteristic,
        )

    variant = f"{args.exposure}_{args.basis}_{args.characteristic or 'all'}"
    logger.info("Scoring %d solutions in: %s", len(folders), args.solutions_dir)
    logger.info("Model: %s, Variant: %s", args.model, variant)

    for folder_name in folders:
        folder = args.solutions_dir / folder_name
        try:
            issue = _load_issue(folder)
            solution = _load_solution(folder)
            source_files = _gather_source_files(args.exposure, folder, issue, solution)

            if args.granularity == "single":
                judgment = judge.judge_single(
                    args.characteristic,
                    issue,
                    solution,
                    folder_name,
                    source_files=source_files,
                )
            else:
                judgment = judge.judge(
                    issue, solution, folder_name, source_files=source_files
                )

            storage.save(judgment)
            logger.info("  %s: %.2f", folder_name, judgment.overall_score)
        except Exception as e:
            logger.error("  %s: FAILED - %s", folder_name, e)


def _cmd_judge_ranking(args) -> None:
    from .judge import Judge, RankingStorage

    if not args.solutions:
        raise ValueError("--solutions is required when --basis ranking")
    if not args.group:
        raise ValueError("--group is required when --basis ranking")

    folder_names = [s.strip() for s in args.solutions.split(",") if s.strip()]
    if len(folder_names) != N_RANKING_SOLUTIONS:
        raise ValueError(
            f"Ranking requires exactly {N_RANKING_SOLUTIONS} solutions, "
            f"got {len(folder_names)}"
        )
    if len(set(folder_names)) != N_RANKING_SOLUTIONS:
        raise ValueError("--solutions must not contain duplicates")

    issues = []
    solutions = []
    source_files_per_solution = []
    for folder_name in folder_names:
        folder = args.solutions_dir / folder_name
        if not folder.exists():
            raise ValueError(f"Solution folder not found: {folder}")
        issue = _load_issue(folder)
        solution = _load_solution(folder)
        issues.append(issue)
        solutions.append(solution)
        if args.exposure.startswith("V2"):
            source_files_per_solution.append(
                _gather_source_files(args.exposure, folder, issue, solution) or {}
            )

    issue_ids = {i.issue_id for i in issues}
    if len(issue_ids) != 1:
        raise ValueError(
            f"All ranking solutions must be for the same issue, found: {issue_ids}"
        )
    issue = issues[0]

    judge = Judge(model=args.model, exposure=args.exposure)
    storage = RankingStorage(args.rankings_dir)

    if not args.force and storage.has_ranking(
        args.group,
        args.exposure,
        args.basis,
        args.granularity,
        args.characteristic,
    ):
        logger.info(
            "Ranking already exists for group %s; use --force to overwrite",
            args.group,
        )
        return

    variant = f"{args.exposure}_{args.basis}_{args.characteristic or 'all'}"
    logger.info("Ranking %d solutions for group: %s", len(folder_names), args.group)
    logger.info("Model: %s, Variant: %s", args.model, variant)

    if args.granularity == "single":
        judgment = judge.rank_single(
            args.characteristic,
            issue,
            solutions,
            folder_names,
            args.group,
            source_files_per_solution=source_files_per_solution or None,
        )
    else:
        judgment = judge.rank(
            issue,
            solutions,
            folder_names,
            args.group,
            source_files_per_solution=source_files_per_solution or None,
        )

    path = storage.save(judgment)
    logger.info("Saved ranking to: %s", path)
    for cr in judgment.rankings:
        order = " > ".join(
            f"{r.solution_id}(#{r.rank})"
            for r in sorted(cr.rankings, key=lambda r: r.rank)
        )
        logger.info("  %s: %s", cr.characteristic_id, order)


def cmd_select(args) -> None:
    """Select answer pairs for survey comparison."""
    from .selection import SelectionStorage, select_pair_for_issue

    issue_ids = (
        [args.issue]
        if args.issue
        else _list_solution_issue_ids(args.solutions_dir)
    )
    storage = SelectionStorage(args.output)

    logger.info("Selecting answer pairs for %d issues", len(issue_ids))
    logger.info("Scoring exposure: %s", args.exposure)

    for issue_id in issue_ids:
        try:
            selected = select_pair_for_issue(
                args.solutions_dir,
                issue_id,
                exposure=args.exposure,
                expected_solutions=args.expected_solutions,
                max_average_gap=args.max_average_gap,
            )
            path = storage.save(selected)
            logger.info(
                "  %s: %s vs %s -> %s",
                issue_id,
                selected.solution_a,
                selected.solution_b,
                path,
            )
        except Exception as e:
            logger.error("  %s: FAILED - %s", issue_id, e)


def _list_solution_issue_ids(solutions_dir: Path) -> list[str]:
    issue_ids = set()
    for folder in sorted(solutions_dir.iterdir()):
        if not folder.is_dir() or not (folder / "solution.json").exists():
            continue
        try:
            with open(folder / "solution.json", encoding="utf-8") as f:
                data = json.load(f)
            if issue_id := data.get("issue_id"):
                issue_ids.add(issue_id)
        except Exception as e:
            logger.warning("Skipping %s while listing issue ids: %s", folder.name, e)
    return sorted(issue_ids)


def main() -> None:
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="routing",
        description="Routing preference research pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- generate ---
    gen_parser = subparsers.add_parser("generate", help="Generate solutions for issues")
    gen_parser.add_argument(
        "--dataset", "-d",
        required=True,
        help="HuggingFace dataset name or path to local JSON file",
    )
    gen_parser.add_argument(
        "--split", "-s",
        default="test",
        help="Dataset split to use (default: test)",
    )
    gen_parser.add_argument(
        "--model", "-m",
        action="append",
        dest="models",
        default=[],
        help="Model to use in LiteLLM format",
    )
    gen_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Maximum number of issues to process",
    )
    gen_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Output directory (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    gen_parser.add_argument(
        "--sandbox",
        choices=["local", "docker"],
        default="local",
        help="Execution environment (default: local)",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # --- judge ---
    judge_parser = subparsers.add_parser("judge", help="Judge solutions")
    judge_parser.add_argument(
        "--solutions-dir", "-s",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Directory containing solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    judge_parser.add_argument(
        "--rankings-dir",
        type=Path,
        default=DEFAULT_RANKINGS_DIR,
        help=f"Directory for ranking results (default: {DEFAULT_RANKINGS_DIR})",
    )
    judge_parser.add_argument(
        "--model", "-m",
        default="openai/gpt-4o",
        help="Model to use for judging (default: openai/gpt-4o)",
    )
    judge_parser.add_argument(
        "--solution",
        type=str,
        help="Score a specific solution folder (scoring only)",
    )
    judge_parser.add_argument(
        "--solutions",
        type=str,
        help=(
            f"Comma-separated list of {N_RANKING_SOLUTIONS} solution folders "
            "to rank (ranking only)"
        ),
    )
    judge_parser.add_argument(
        "--group",
        type=str,
        help="Group identifier for a ranking (required when --basis ranking)",
    )
    judge_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-run even if this judgment variant already exists",
    )
    judge_parser.add_argument(
        "--exposure",
        choices=["V1", "V2.0", "V2.1"],
        default="V1",
        help="Code exposure: V1 (none), V2.0 (patch-affected), V2.1 (agent-explored)",
    )
    judge_parser.add_argument(
        "--basis",
        choices=["scoring", "ranking"],
        default="scoring",
        help="Judgment basis: scoring (per solution) or ranking (across N solutions)",
    )
    judge_parser.add_argument(
        "--granularity",
        choices=["all", "single"],
        default="all",
        help="Judge all characteristics at once or one at a time",
    )
    judge_parser.add_argument(
        "--characteristic",
        choices=CHARACTERISTICS,
        help="Characteristic to judge (required when --granularity single)",
    )
    judge_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    judge_parser.set_defaults(func=cmd_judge)

    # --- select ---
    select_parser = subparsers.add_parser(
        "select",
        help="Select answer pairs for the survey",
    )
    select_parser.add_argument(
        "--solutions-dir", "-s",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Directory containing solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    select_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_SELECTIONS_DIR,
        help=f"Output directory for selected pairs (default: {DEFAULT_SELECTIONS_DIR})",
    )
    select_parser.add_argument(
        "--issue",
        help="Select a pair for one issue id; defaults to all issues in solutions-dir",
    )
    select_parser.add_argument(
        "--exposure",
        default="V1",
        help="Scoring exposure/version to use, matching judgment filenames",
    )
    select_parser.add_argument(
        "--expected-solutions",
        type=int,
        default=7,
        help="Required number of scored solutions per issue (default: 7)",
    )
    select_parser.add_argument(
        "--max-average-gap",
        type=float,
        default=0.75,
        help=(
            "Maximum subjective-average gap for preferred pairs; if no pair "
            "matches, selection falls back to all pairs (default: 0.75)"
        ),
    )
    select_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    select_parser.set_defaults(func=cmd_select)

    args = parser.parse_args()

    if hasattr(args, "verbose") and args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

    args.func(args)
    logger.info("Done!")


if __name__ == "__main__":
    main()
