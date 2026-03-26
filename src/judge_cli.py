"""CLI for judging solutions."""

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from .models import Issue, Solution
from .judge_pipeline import JudgePipeline
from .judge.ranking_judge import RankingJudge
from .judge.ranking_storage import RankingStorage

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"
DEFAULT_RANKINGS_DIR = PROJECT_ROOT / "data" / "rankings"

logger = logging.getLogger(__name__)


def find_solutions_for_issue(
    solutions_dir: Path, issue_id: str
) -> list[tuple[Path, Issue, Solution]]:
    """Find all solutions for a given issue ID."""
    results = []
    for folder in solutions_dir.iterdir():
        if not folder.is_dir():
            continue
        if issue_id not in folder.name:
            continue

        solution_file = folder / "solution.json"
        issue_file = folder / "issue.json"
        if not solution_file.exists() or not issue_file.exists():
            continue

        with open(issue_file, encoding="utf-8") as f:
            issue = Issue(**json.load(f))
        with open(solution_file, encoding="utf-8") as f:
            solution = Solution(**json.load(f))

        if issue.id == issue_id:
            results.append((folder, issue, solution))

    return results


def run_ranking(args) -> None:
    """Run comparative ranking for an issue."""
    print(f"Finding solutions for issue: {args.rank}")
    found = find_solutions_for_issue(args.solutions_dir, args.rank)

    if not found:
        print(f"No solutions found for issue: {args.rank}")
        return

    print(f"Found {len(found)} solutions:")
    for folder, _, solution in found:
        print(f"  - {solution.model} ({folder.name})")

    if len(found) < 2:
        print("Need at least 2 solutions to rank. Exiting.")
        return

    # Extract issue and solutions
    issue = found[0][1]
    solutions = [sol for _, _, sol in found]

    # Run ranking judge
    print(f"\nRanking with judge model: {args.judge_model}")
    judge = RankingJudge(model=args.judge_model)
    judgment = judge.judge(issue, solutions)

    # Save results
    storage = RankingStorage(args.rankings_dir)
    path = storage.save(judgment)
    print(f"\nSaved ranking to: {path}")

    # Print summary
    print("\n=== Rankings ===")
    for ranking in judgment.rankings:
        print(f"\n{ranking.characteristic_id}:")
        sorted_models = sorted(ranking.ranks.items(), key=lambda x: x[1])
        for model, rank in sorted_models:
            print(f"  {rank}. {model}")

    print("\n=== Overall (average rank) ===")
    sorted_overall = sorted(judgment.overall_ranks.items(), key=lambda x: x[1])
    for model, avg_rank in sorted_overall:
        print(f"  {avg_rank:.2f} - {model}")


def run_scoring(args) -> None:
    """Run absolute scoring for solutions."""
    pipeline = JudgePipeline(args.solutions_dir, args.judge_model)

    if args.solution:
        print(f"Judging solution: {args.solution}")
        pipeline.run_single(args.solution)
    else:
        print(f"Judging solutions in: {args.solutions_dir}")
        print(f"Judge model: {args.judge_model}")
        print()
        pipeline.run(skip_existing=not args.no_skip_existing)


def main() -> None:
    """Main entry point for the judge CLI."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Score or rank solutions using LLM as a Judge",
    )
    parser.add_argument(
        "--solutions-dir", "-s",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Directory containing solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    parser.add_argument(
        "--rankings-dir",
        type=Path,
        default=DEFAULT_RANKINGS_DIR,
        help=f"Directory to store rankings (default: {DEFAULT_RANKINGS_DIR})",
    )
    parser.add_argument(
        "--judge-model", "-j",
        default="openai/gpt-4o",
        help="Model to use for judging (default: openai/gpt-4o)",
    )
    parser.add_argument(
        "--solution",
        type=str,
        help="Score a specific solution folder",
    )
    parser.add_argument(
        "--rank",
        type=str,
        metavar="ISSUE_ID",
        help="Rank all solutions for an issue comparatively (e.g., sympy__sympy-11400)",
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

    if args.rank:
        run_ranking(args)
    else:
        run_scoring(args)

    print("\nDone!")


if __name__ == "__main__":
    main()
