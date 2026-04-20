"""Unified CLI for routing-preference."""

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"

CHARACTERISTICS = ["intent", "correctness", "scope", "quality"]


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
    from .judge.source_files import extract_changed_files, fetch_source_files

    if args.basis == "rank":
        raise NotImplementedError("Ranking is not implemented yet")

    if args.granularity == "single" and not args.characteristic:
        raise ValueError("--characteristic is required when --granularity single")

    judge = Judge(model=args.model, exposure=args.exposure)
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
        folders = storage.list_unjudged(
            exposure=args.exposure,
            basis=args.basis,
            granularity=args.granularity,
            characteristic_id=args.characteristic,
        )

    variant = f"{args.exposure}_{args.basis}_{args.characteristic or 'all'}"
    logger.info("Judging %d solutions in: %s", len(folders), args.solutions_dir)
    logger.info("Model: %s, Variant: %s", args.model, variant)

    for folder_name in folders:
        folder = args.solutions_dir / folder_name
        try:
            with open(folder / "issue.json", encoding="utf-8") as f:
                issue = Issue(**json.load(f))
            with open(folder / "solution.json", encoding="utf-8") as f:
                solution = Solution(**json.load(f))

            source_files = None
            if args.exposure.startswith("V2"):
                if not issue.base_commit:
                    raise ValueError(
                        f"V2 scoring requires base_commit on issue {issue.issue_id}"
                    )
                paths = extract_changed_files(solution.diff)
                source_files = fetch_source_files(
                    issue.repo, issue.base_commit, paths
                )

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
        help="Re-judge solutions that already have this judgment variant",
    )
    judge_parser.add_argument(
        "--exposure",
        choices=["V1", "V2.0", "V2.1"],
        default="V1",
        help="Code exposure: V1 (none), V2.0 (patch-affected), V2.1 (agent-explored)",
    )
    judge_parser.add_argument(
        "--basis",
        choices=["score", "rank"],
        default="score",
        help="Scoring basis: score or rank (rank not yet implemented)",
    )
    judge_parser.add_argument(
        "--granularity",
        choices=["all", "single"],
        default="all",
        help="Score all characteristics at once or one at a time",
    )
    judge_parser.add_argument(
        "--characteristic",
        choices=CHARACTERISTICS,
        help="Characteristic to score (required when --granularity single)",
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
