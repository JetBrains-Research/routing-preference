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


def cmd_judge(args) -> None:
    """Judge solutions."""
    if args.rank:
        _run_ranking(args)
    else:
        _run_scoring(args)


def _run_scoring(args) -> None:
    """Run absolute scoring for solutions."""
    from .models import Issue, Solution
    from .judge import Judge, ScoringMode, JudgmentStorage

    judge = Judge(
        model=args.model,
        mode=ScoringMode(args.mode),
        prompt_version=args.prompt_version,
    )
    storage = JudgmentStorage(args.solutions_dir)

    # Get folders to process
    if args.solution:
        folders = [args.solution]
    elif args.force:
        folders = [
            f.name for f in sorted(args.solutions_dir.iterdir())
            if f.is_dir() and (f / "solution.json").exists()
        ]
    else:
        folders = storage.list_unjudged()

    logger.info("Judging %d solutions in: %s", len(folders), args.solutions_dir)
    logger.info("Model: %s, Mode: %s", args.model, args.mode)

    for folder_name in folders:
        folder = args.solutions_dir / folder_name
        try:
            with open(folder / "issue.json", encoding="utf-8") as f:
                issue = Issue(**json.load(f))
            with open(folder / "solution.json", encoding="utf-8") as f:
                solution = Solution(**json.load(f))

            judgment = judge.judge(issue, solution, folder_name)
            path = storage.save(judgment)
            logger.info("  %s: %.2f", folder_name, judgment.overall_score)
        except Exception as e:
            logger.error("  %s: FAILED - %s", folder_name, e)


def _run_ranking(args) -> None:
    """Run comparative ranking for an issue."""
    from .models import Issue, Solution
    from .judge.ranking import RankingJudge, RankingStorage

    logger.info("Finding solutions for issue: %s", args.rank)
    found = _find_solutions_for_issue(args.solutions_dir, args.rank)

    if not found:
        logger.info("No solutions found for issue: %s", args.rank)
        return

    logger.info("Found %d solutions:", len(found))
    for folder, _, solution in found:
        logger.info("  - %s (%s)", solution.model, folder.name)

    if len(found) < 2:
        logger.info("Need at least 2 solutions to rank. Exiting.")
        return

    issue = found[0][1]
    solutions = [sol for _, _, sol in found]

    logger.info("Ranking with model: %s", args.model)
    judge = RankingJudge(model=args.model)
    judgment = judge.judge(issue, solutions)

    storage = RankingStorage(args.rankings_dir)
    path = storage.save(judgment)
    logger.info("Saved ranking to: %s", path)

    logger.info("=== Rankings ===")
    for ranking in judgment.rankings:
        logger.info("%s:", ranking.characteristic_id)
        sorted_models = sorted(ranking.ranks.items(), key=lambda x: x[1])
        for model, rank in sorted_models:
            logger.info("  %d. %s", rank, model)

    logger.info("=== Overall (average rank) ===")
    sorted_overall = sorted(judgment.overall_ranks.items(), key=lambda x: x[1])
    for model, avg_rank in sorted_overall:
        logger.info("  %.2f - %s", avg_rank, model)


def _find_solutions_for_issue(solutions_dir: Path, issue_id: str) -> list:
    """Find all solutions for a given issue ID."""
    from .models import Issue, Solution

    results = []
    for folder in sorted(solutions_dir.iterdir()):
        if not folder.is_dir():
            continue

        solution_file = folder / "solution.json"
        issue_file = folder / "issue.json"
        if not solution_file.exists() or not issue_file.exists():
            continue

        try:
            with open(issue_file, encoding="utf-8") as f:
                issue = Issue(**json.load(f))
            with open(solution_file, encoding="utf-8") as f:
                solution = Solution(**json.load(f))
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("Skipping %s due to error: %s", folder.name, e)
            continue

        if issue.issue_id == issue_id:
            results.append((folder, issue, solution))

    return results

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
        "--dataset", "-d", required=True,
        help="HuggingFace dataset name or path to local JSON file",
    )
    gen_parser.add_argument(
        "--split", "-s", default="test",
        help="Dataset split to use (default: test)",
    )
    gen_parser.add_argument(
        "--model", "-m", action="append", dest="models", default=[],
        help="Model to use in LiteLLM format",
    )
    gen_parser.add_argument(
        "--limit", "-l", type=int, default=None,
        help="Maximum number of issues to process",
    )
    gen_parser.add_argument(
        "--output", "-o", type=Path, default=DEFAULT_SOLUTIONS_DIR,
        help=f"Output directory (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    gen_parser.add_argument(
        "--sandbox", choices=["local", "docker"], default="local",
        help="Execution environment (default: local)",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # --- judge ---
    judge_parser = subparsers.add_parser("judge", help="Judge solutions")
    judge_parser.add_argument(
        "--solutions-dir", "-s", type=Path, default=DEFAULT_SOLUTIONS_DIR,
        help=f"Directory containing solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    judge_parser.add_argument(
        "--rankings-dir", type=Path, default=DEFAULT_RANKINGS_DIR,
        help=f"Directory for rankings (default: {DEFAULT_RANKINGS_DIR})",
    )
    judge_parser.add_argument(
        "--model", "-m", default="openai/gpt-4o",
        help="Model to use for judging (default: openai/gpt-4o)",
    )
    judge_parser.add_argument(
        "--solution", type=str,
        help="Score a specific solution folder",
    )
    judge_parser.add_argument(
        "--rank", type=str, metavar="ISSUE_ID",
        help="Rank all solutions for an issue comparatively",
    )
    judge_parser.add_argument(
        "--force", "-f", action="store_true",
        help="Re-judge solutions that already have judgments",
    )
    judge_parser.add_argument(
        "--mode", choices=["single", "batch"], default="batch",
        help="Scoring mode (default: batch)",
    )
    judge_parser.add_argument(
        "--prompt-version", type=str, default=None,
        help="Prompt template version",
    )
    judge_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    judge_parser.set_defaults(func=cmd_judge)

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
