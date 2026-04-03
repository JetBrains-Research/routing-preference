"""CLI for issue collection."""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from .classifier import IssueClassifier
from .collector import IssueCollector
from .filters import IssueFilter
from .reviewer import ReviewerManager
from .storage import HuggingFaceStorage, IssueStorage

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_ISSUES_DIR = PROJECT_ROOT / "data" / "issues"
DEFAULT_REVIEWERS_DIR = PROJECT_ROOT / "data" / "reviewers"

# Curated list of repositories
DEFAULT_REPOS = [
    # JetBrains
    "JetBrains/teamcity-messages",
    # Web frameworks
    "pallets/flask",
    "encode/httpx",
    "tiangolo/fastapi",
    # Data
    "pola-rs/polars",
    # Tooling
    "pytest-dev/pytest",
    "astral-sh/ruff",
    "python/mypy",
    "python-poetry/poetry",
    # CLI
    "Textualize/rich",
    "tiangolo/typer",
    # Async
    "aio-libs/aiohttp",
]


def cmd_collect(args) -> None:
    """Collect issues from repositories."""
    collector = IssueCollector(cutoff_days=args.days)
    storage = IssueStorage(args.output)
    filter_ = IssueFilter(
        min_body_length=args.min_body_length,
        require_engagement=not args.no_engagement_filter,
    )
    classifier = IssueClassifier()

    repos = args.repos if args.repos else DEFAULT_REPOS

    all_issues = []

    for repo in repos:
        logger.info("=" * 60)
        logger.info("Collecting from: %s", repo)
        logger.info("=" * 60)

        try:
            owner, name = repo.split("/")
        except ValueError:
            logger.error("Invalid repo format: %s (expected owner/name)", repo)
            continue

        # Collect issues
        collected = list(collector.collect_issues(
            owner,
            name,
            state=args.state,
            max_issues=args.max_per_repo,
        ))
        logger.info("Collected: %d issues", len(collected))

        # Filter issues
        passed, rejected = filter_.filter_batch(collected)
        logger.info("After filtering: %d issues", len(passed))

        # Classify issues
        classified = classifier.classify_batch(passed, use_llm_fallback=args.use_llm)
        logger.info("Classified: %d issues", len(classified))

        # Get base commits if requested
        if args.fetch_commits:
            logger.info("Fetching base commits...")
            for issue in classified:
                collector.enrich_with_base_commit(issue)

        all_issues.extend(classified)

    # Save results
    logger.info("=" * 60)
    logger.info("Total collected: %d issues", len(all_issues))
    logger.info("=" * 60)

    if args.batch_file:
        storage.save_batch(all_issues, args.batch_file)
    else:
        for issue in all_issues:
            storage.save(issue)

    # Log filter stats
    logger.info("Filter Statistics:")
    logger.info(filter_.get_stats().summary())


def cmd_filter(args) -> None:
    """Apply filters to existing issues."""
    storage = IssueStorage(args.input)
    filter_ = IssueFilter(
        min_body_length=args.min_body_length,
        require_engagement=not args.no_engagement_filter,
    )

    issues = list(storage.load_all())
    logger.info("Loaded %d issues", len(issues))

    passed, rejected = filter_.filter_batch(issues)
    logger.info("Passed: %d", len(passed))
    logger.info("Rejected: %d", len(rejected))

    if args.output:
        out_storage = IssueStorage(args.output)
        out_storage.save_batch(passed, "filtered_issues.json")

    logger.info("Filter Statistics:")
    logger.info(filter_.get_stats().summary())

    if args.show_rejected:
        logger.info("Rejected issues:")
        for issue, reason in rejected[:20]:
            logger.info("  %s: %s", issue.issue_id, reason)


def cmd_classify(args) -> None:
    """Classify issues by type and complexity."""
    storage = IssueStorage(args.input)
    classifier = IssueClassifier(llm_model=args.model)

    issues = list(storage.load_all())
    logger.info("Loaded %d issues", len(issues))

    classified = classifier.classify_batch(issues, use_llm_fallback=args.use_llm)

    # Log stats
    type_counts = {}
    complexity_counts = {}
    for issue in classified:
        type_counts[issue.issue_type.value] = type_counts.get(issue.issue_type.value, 0) + 1
        complexity_counts[issue.complexity.value] = complexity_counts.get(issue.complexity.value, 0) + 1

    logger.info("Issue Types:")
    for t, count in sorted(type_counts.items()):
        logger.info("  %s: %d", t, count)

    logger.info("Complexity:")
    for c, count in sorted(complexity_counts.items()):
        logger.info("  %s: %d", c, count)

    if args.output:
        out_storage = IssueStorage(args.output)
        out_storage.save_batch(classified, "classified_issues.json")


def cmd_reviewers(args) -> None:
    """Manage reviewers."""
    manager = ReviewerManager(args.reviewers_dir)

    if args.action == "import":
        if not args.repos:
            logger.error("--repos required for import action")
            return
        collector = IssueCollector()
        for repo in args.repos:
            owner, name = repo.split("/")
            maintainers = collector.get_maintainers(owner, name, limit=args.limit)
            manager.import_maintainers(repo, maintainers)
            logger.info("Imported %d maintainers from %s", len(maintainers), repo)

    elif args.action == "consent":
        if not args.usernames:
            logger.error("--usernames required for consent action")
            return
        for username in args.usernames:
            if manager.set_consent(username, True):
                logger.info("Granted consent for %s", username)
            else:
                logger.warning("Reviewer not found: %s", username)

    elif args.action == "list":
        reviewers = manager.list_reviewers()
        logger.info("Total reviewers: %d", len(reviewers))
        for r in reviewers:
            status = "consented" if r.consent_given else "pending"
            logger.info("  %s (%s): %s", r.github_username, status, r.repos)

    elif args.action == "stats":
        stats = manager.get_stats()
        logger.info("Reviewer Statistics:")
        for key, value in stats.items():
            logger.info("  %s: %s", key, value)


def cmd_assign(args) -> None:
    """Assign reviewers to issues."""
    storage = IssueStorage(args.input)
    manager = ReviewerManager(args.reviewers_dir)

    issues = list(storage.load_all())
    logger.info("Loaded %d issues", len(issues))

    assigned, unassigned = manager.bulk_assign(issues)

    logger.info("Assigned: %d", len(assigned))
    logger.info("Unassigned: %d", len(unassigned))

    output_dir = args.output if args.output else args.input
    out_storage = IssueStorage(output_dir)
    out_storage.save_batch(assigned, "assigned_issues.json")


def cmd_export(args) -> None:
    """Export issues to HuggingFace format."""
    storage = IssueStorage(args.input)
    hf_storage = HuggingFaceStorage(args.dataset_name)

    issues = storage.load_batch(args.batch_file) if args.batch_file else list(storage.load_all())
    logger.info("Loaded %d issues", len(issues))

    path = hf_storage.export(
        issues,
        push_to_hub=args.push,
        token=args.token,
    )
    logger.info("Exported to %s", path)


def main() -> None:
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Issue collection pipeline for routing-preference",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Collect issues from repositories")
    collect_parser.add_argument(
        "--repos", "-r",
        nargs="+",
        help="Repositories to collect from (owner/name format)",
    )
    collect_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_ISSUES_DIR,
        help="Output directory",
    )
    collect_parser.add_argument(
        "--state",
        choices=["open", "closed", "all"],
        default="all",
        help="Issue state filter",
    )
    collect_parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="Collect issues from last N days (default: 730)",
    )
    collect_parser.add_argument(
        "--max-per-repo",
        type=int,
        default=200,
        help="Max issues per repository",
    )
    collect_parser.add_argument(
        "--min-body-length",
        type=int,
        default=100,
        help="Minimum issue body length",
    )
    collect_parser.add_argument(
        "--no-engagement-filter",
        action="store_true",
        help="Don't require reactions/comments",
    )
    collect_parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for issue type classification",
    )
    collect_parser.add_argument(
        "--fetch-commits",
        action="store_true",
        help="Fetch base commit for each issue",
    )
    collect_parser.add_argument(
        "--batch-file",
        type=str,
        help="Save all issues to a single batch file",
    )
    collect_parser.set_defaults(func=cmd_collect)

    # Filter command
    filter_parser = subparsers.add_parser("filter", help="Filter existing issues")
    filter_parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_ISSUES_DIR,
        help="Input directory",
    )
    filter_parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output directory",
    )
    filter_parser.add_argument(
        "--min-body-length",
        type=int,
        default=100,
        help="Minimum issue body length",
    )
    filter_parser.add_argument(
        "--no-engagement-filter",
        action="store_true",
        help="Don't require reactions/comments",
    )
    filter_parser.add_argument(
        "--show-rejected",
        action="store_true",
        help="Show rejected issues",
    )
    filter_parser.set_defaults(func=cmd_filter)

    # Classify command
    classify_parser = subparsers.add_parser("classify", help="Classify issues")
    classify_parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_ISSUES_DIR,
        help="Input directory",
    )
    classify_parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output directory",
    )
    classify_parser.add_argument(
        "--model",
        default="openai/gpt-4o-mini",
        help="LLM model for classification",
    )
    classify_parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for unlabeled issues",
    )
    classify_parser.set_defaults(func=cmd_classify)

    # Reviewers command
    reviewers_parser = subparsers.add_parser("reviewers", help="Manage reviewers")
    reviewers_parser.add_argument(
        "action",
        choices=["import", "consent", "list", "stats"],
        help="Action to perform",
    )
    reviewers_parser.add_argument(
        "--repos", "-r",
        nargs="+",
        help="Repositories for import action",
    )
    reviewers_parser.add_argument(
        "--usernames", "-u",
        nargs="+",
        help="Usernames for consent action",
    )
    reviewers_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max maintainers per repo",
    )
    reviewers_parser.add_argument(
        "--reviewers-dir",
        type=Path,
        default=DEFAULT_REVIEWERS_DIR,
        help="Reviewers storage directory",
    )
    reviewers_parser.set_defaults(func=cmd_reviewers)

    # Assign command
    assign_parser = subparsers.add_parser("assign", help="Assign reviewers to issues")
    assign_parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_ISSUES_DIR,
        help="Input directory",
    )
    assign_parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output directory",
    )
    assign_parser.add_argument(
        "--reviewers-dir",
        type=Path,
        default=DEFAULT_REVIEWERS_DIR,
        help="Reviewers storage directory",
    )
    assign_parser.set_defaults(func=cmd_assign)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export to HuggingFace")
    export_parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_ISSUES_DIR,
        help="Input directory",
    )
    export_parser.add_argument(
        "--dataset-name",
        required=True,
        help="HuggingFace dataset name (org/name)",
    )
    export_parser.add_argument(
        "--batch-file",
        type=str,
        help="Load from batch file instead of individual files",
    )
    export_parser.add_argument(
        "--push",
        action="store_true",
        help="Push to HuggingFace Hub",
    )
    export_parser.add_argument(
        "--token",
        help="HuggingFace token",
    )
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    args.func(args)


if __name__ == "__main__":
    main()
