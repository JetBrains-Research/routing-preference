"""Command-line interface for solution generation."""

import argparse
from pathlib import Path

from .pipeline import Pipeline

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Generate solutions for GitHub issues using mini-swe-agent + LiteLLM",
    )
    parser.add_argument(
        "--repo", "-r",
        required=True,
        help="GitHub repository (owner/repo)",
    )
    parser.add_argument(
        "--issue", "-i",
        type=int,
        required=True,
        help="Issue number to solve",
    )
    parser.add_argument(
        "--model", "-m",
        action="append",
        dest="models",
        default=[],
        help="Model to use (can specify multiple). Default: gpt-4o-mini",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Output directory for solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    parser.add_argument(
        "--litellm-url",
        default="http://localhost:4000",
        help="LiteLLM proxy URL (default: http://localhost:4000)",
    )

    args = parser.parse_args()

    # Parse models - default to gpt-4o-mini if none specified
    models = []
    for m in args.models or ["gpt-4o-mini"]:
        if ":" in m:
            name, provider = m.split(":", 1)
        else:
            name, provider = m, "openai"
        models.append((name, provider))

    # Run pipeline
    print(f"Generating solutions for {args.repo}#{args.issue}")
    print(f"Models: {', '.join(f'{name}:{provider}' for name, provider in models)}")
    print()

    pipeline = Pipeline(
        solutions_dir=args.output,
        litellm_base_url=args.litellm_url,
    )
    pipeline.run_single(
        repo=args.repo,
        issue_number=args.issue,
        models=models,
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
