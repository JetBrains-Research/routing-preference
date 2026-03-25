"""CLI for judging solutions."""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from .judge_pipeline import JudgePipeline

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"


def main() -> None:
    """Main entry point for the judge CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Score solutions using LLM as a Judge",
    )
    parser.add_argument(
        "--solutions-dir", "-s",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Directory containing solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    parser.add_argument(
        "--judge-model", "-j",
        default="openai/gpt-4o",
        help="Model to use for judging (default: openai/gpt-4o)",
    )
    parser.add_argument(
        "--solution",
        type=str,
        help="Judge a specific solution folder (default: all)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-judge solutions that already have judgments",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    pipeline = JudgePipeline(args.solutions_dir, args.judge_model)

    if args.solution:
        print(f"Judging solution: {args.solution}")
        pipeline.run_single(args.solution)
    else:
        print(f"Judging solutions in: {args.solutions_dir}")
        print(f"Judge model: {args.judge_model}")
        print()
        pipeline.run(skip_existing=not args.no_skip_existing)

    print("\nDone!")


if __name__ == "__main__":
    main()
