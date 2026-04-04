"""Unified CLI for routing-preference."""

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"


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
    from .models import Issue, Solution
    from .judge import Judge, JudgmentStorage

    judge = Judge(model=args.model, version=args.version)
    storage = JudgmentStorage(args.solutions_dir)

    if args.solution:
        folders = [args.solution]
    elif args.force:
        folders = [
            f.name
            for f in sorted(args.solutions_dir.iterdir())
            if f.is_dir() and (f / "solution.json").exists()
        ]
    else:
        folders = storage.list_unjudged()

    logger.info("Judging %d solutions in: %s", len(folders), args.solutions_dir)
    logger.info("Model: %s, Version: %s", args.model, args.version)

    for folder_name in folders:
        folder = args.solutions_dir / folder_name
        try:
            with open(folder / "issue.json", encoding="utf-8") as f:
                issue = Issue(**json.load(f))
            with open(folder / "solution.json", encoding="utf-8") as f:
                solution = Solution(**json.load(f))

            judgment = judge.judge(issue, solution, folder_name)
            storage.save(judgment)
            logger.info("  %s: %.2f", folder_name, judgment.overall_score)
        except Exception as e:
            logger.error("  %s: FAILED - %s", folder_name, e)


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
        "--model", "-m",
        default="openai/gpt-4o",
        help="Model to use for judging (default: openai/gpt-4o)",
    )
    judge_parser.add_argument(
        "--solution",
        type=str,
        help="Score a specific solution folder",
    )
    judge_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-judge solutions that already have judgments",
    )
    judge_parser.add_argument(
        "--version",
        choices=["V1", "V2.0", "V2.1"],
        default="V1",
        help="Scoring version: V1 (issue+diff) or V2.x (issue+diff+sources)",
    )
    judge_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    judge_parser.set_defaults(func=cmd_judge)

    args = parser.parse_args()

    if hasattr(args, "verbose") and args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    args.func(args)
    logger.info("Done!")


if __name__ == "__main__":
    main()
