"""Command-line interface for solution generation."""

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .dataset import load_issues
from .pipeline import Pipeline

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"


def main() -> None:
    """Main entry point for the CLI."""
    # Load environment variables from a .env file, if present
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Generate solutions for GitHub issues using mini-swe-agent",
    )
    parser.add_argument(
        "--dataset", "-d",
        required=True,
        help="HuggingFace dataset name or path to local JSON file",
    )
    parser.add_argument(
        "--split", "-s",
        default="test",
        help="Dataset split to use (default: test)",
    )
    parser.add_argument(
        "--model", "-m",
        action="append",
        dest="models",
        default=[],
        help="Model to use in LiteLLM format.",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Maximum number of issues to process (default: all)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Output directory for solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )

    args = parser.parse_args()

    # Default model if none specified
    models = args.models or ["openai/gpt-4o-mini"]

    # Load dataset
    print(f"Loading dataset: {args.dataset} (split: {args.split})")
    dataset = load_issues(args.dataset, split=args.split)
    print(f"Found {len(dataset)} issues")

    # Run pipeline
    print(f"Models: {', '.join(models)}")
    print()

    pipeline = Pipeline(solutions_dir=args.output)
    pipeline.run(dataset=dataset, models=models, limit=args.limit)

    print("\nDone!")


if __name__ == "__main__":
    main()
