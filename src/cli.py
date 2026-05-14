"""Unified CLI for routing-preference."""

import argparse
import json
import logging
from dataclasses import fields, replace
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_SOLUTIONS_DIR = PROJECT_ROOT / "data" / "solutions"
DEFAULT_JUDGMENTS_DIR = PROJECT_ROOT / "data" / "judgments"
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
    valid_fields = {field.name for field in fields(Issue)}
    return Issue(**{key: value for key, value in data.items() if key in valid_fields})


def _load_solution(folder: Path):
    from .models import Solution

    with open(folder / "solution.json", encoding="utf-8") as f:
        data = json.load(f)
    metrics_path = folder / "objective_metrics.json"
    if metrics_path.exists() and "objective_metrics" not in data:
        with open(metrics_path, encoding="utf-8") as f:
            data["objective_metrics"] = json.load(f)
    return Solution(**data)


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
    """Judge solutions, scoring or ranking based on --basis."""
    if args.granularity == "single" and not args.characteristic:
        raise ValueError("--characteristic is required when --granularity single")

    if args.basis == "scoring":
        _cmd_judge_scoring(args)
    else:
        _cmd_judge_ranking(args)


def _cmd_judge_scoring(args) -> None:
    from .judge import Judge, ScoringStorage
    from .storage import iter_solution_paths, solution_id_from_run_dir

    judge = Judge(model=args.model, exposure=args.exposure)
    storage = ScoringStorage(args.judgments_dir)

    if args.solution:
        folders = [_resolve_solution_path(args.solutions_dir, args.solution)]
    elif args.force:
        folders = [
            folder for folder in iter_solution_paths(args.solutions_dir)
        ]
    else:
        folders = []
        for folder in iter_solution_paths(args.solutions_dir):
            issue = _load_issue(folder)
            solution_id = solution_id_from_run_dir(folder)
            if not storage.has_judgment(
                issue.issue_id,
                solution_id,
                args.model,
                args.exposure,
                args.granularity,
                args.characteristic,
            ):
                folders.append(folder)

    variant = f"{args.exposure}_{args.basis}_{args.characteristic or 'all'}"
    logger.info("Scoring %d solutions in: %s", len(folders), args.solutions_dir)
    logger.info("Model: %s, Variant: %s", args.model, variant)

    for folder in folders:
        solution_id = solution_id_from_run_dir(folder)
        try:
            issue = _load_issue(folder)
            solution = _load_solution(folder)
            source_files = _gather_source_files(args.exposure, folder, issue, solution)

            if args.granularity == "single":
                judgment = judge.score_single(
                    args.characteristic,
                    issue,
                    solution,
                    solution_id,
                    source_files=source_files,
                )
            else:
                judgment = judge.score(
                    issue, solution, solution_id, source_files=source_files
                )

            storage.save(judgment)
            logger.info("  %s: %.2f", solution_id, judgment.overall_score)
        except Exception as e:
            logger.error("  %s: FAILED - %s", folder, e)


def _cmd_judge_ranking(args) -> None:
    from .judge import Judge, RankingStorage
    from .storage import solution_id_from_run_dir

    if not args.solutions:
        raise ValueError("--solutions is required when --basis ranking")
    if not args.group:
        raise ValueError("--group is required when --basis ranking")

    solution_paths = [
        _resolve_solution_path(args.solutions_dir, s.strip())
        for s in args.solutions.split(",")
        if s.strip()
    ]
    if len(solution_paths) != N_RANKING_SOLUTIONS:
        raise ValueError(
            f"Ranking requires exactly {N_RANKING_SOLUTIONS} solutions, "
            f"got {len(solution_paths)}"
        )
    solution_ids = [solution_id_from_run_dir(path) for path in solution_paths]
    if len(set(solution_ids)) != N_RANKING_SOLUTIONS:
        raise ValueError("--solutions must not contain duplicates")

    issues = []
    solutions = []
    source_files_per_solution = []
    for folder in solution_paths:
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
    storage = RankingStorage(args.judgments_dir)

    if not args.force and storage.has_ranking(
        issue.issue_id,
        args.group,
        args.model,
        args.exposure,
        args.granularity,
        args.characteristic,
    ):
        logger.info(
            "Ranking already exists for group %s; use --force to overwrite",
            args.group,
        )
        return

    variant = f"{args.exposure}_{args.basis}_{args.characteristic or 'all'}"
    logger.info("Ranking %d solutions for group: %s", len(solution_ids), args.group)
    logger.info("Model: %s, Variant: %s", args.model, variant)

    if args.granularity == "single":
        judgment = judge.rank_single(
            args.characteristic,
            issue,
            solutions,
            solution_ids,
            args.group,
            source_files_per_solution=source_files_per_solution or None,
        )
    else:
        judgment = judge.rank(
            issue,
            solutions,
            solution_ids,
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
    """Select two answers for comparison."""
    if args.selection_method != "greedy" and not args.global_balanced:
        raise ValueError("--selection-method is only supported with --global-balanced")

    from .selection import (
        SelectionStorage,
        generate_candidates_for_issue,
        load_selection_config,
        select_balanced_pairs,
        select_balanced_pairs_cpsat,
        select_best_candidate,
        selection_source_run_id,
    )
    from .selection.models import SelectedPair

    config = load_selection_config(args.selection_config)
    max_average_gap = (
        args.max_average_gap
        if args.max_average_gap is not None
        else config.max_average_gap
    )
    min_subscore_diversity = (
        args.min_subscore_diversity
        if args.min_subscore_diversity is not None
        else config.min_subscore_diversity
    )
    effective_config = replace(
        config,
        max_average_gap=max_average_gap,
        min_subscore_diversity=min_subscore_diversity,
    )

    issue_ids = (
        [args.issue]
        if args.issue
        else _list_solution_issue_ids(args.solutions_dir)
    )
    storage = SelectionStorage(args.output)
    run_id = selection_source_run_id(
        "scoring",
        args.judge_model,
        args.exposure,
        "all",
    )

    logger.info("Selecting answer pairs for %d issues", len(issue_ids))
    logger.info("Scoring exposure: %s", args.exposure)
    logger.info("Selection config: %s", args.selection_config)
    logger.info("Max average gap: %.3f", max_average_gap)
    logger.info("Min subscore diversity: %.3f", min_subscore_diversity)

    if args.global_balanced:
        issue_candidates = {}
        for issue_id in issue_ids:
            try:
                candidates = generate_candidates_for_issue(
                    args.solutions_dir,
                    args.judgments_dir,
                    issue_id,
                    judge_model=args.judge_model,
                    exposure=args.exposure,
                    expected_solutions=args.expected_solutions,
                    max_average_gap=max_average_gap,
                    min_subscore_diversity=min_subscore_diversity,
                )
                storage.save_candidates(issue_id, run_id, candidates)
                issue_candidates[issue_id] = candidates
            except Exception as e:
                logger.error("  %s: FAILED - %s", issue_id, e)

        if not issue_candidates:
            raise ValueError("No issues had enough scored candidates for selection")

        if args.selection_method == "cpsat":
            result = select_balanced_pairs_cpsat(issue_candidates, effective_config)
            method = "cpsat_v1"
        else:
            result = select_balanced_pairs(issue_candidates, effective_config)
            method = "greedy_balanced_v1"
        global_run_id = args.selection_run_id or f"{method}__{run_id}"
        path = storage.save_global_run(global_run_id, result, method=method)
        logger.info("Saved global balanced selection run: %s", path)
        logger.info("Model usage: %s", result.model_usage)
        logger.info("Quality band usage: %s", result.quality_band_usage)
        return

    for issue_id in issue_ids:
        try:
            candidates = generate_candidates_for_issue(
                args.solutions_dir,
                args.judgments_dir,
                issue_id,
                judge_model=args.judge_model,
                exposure=args.exposure,
                expected_solutions=args.expected_solutions,
                max_average_gap=max_average_gap,
                min_subscore_diversity=min_subscore_diversity,
            )
            selected_candidate = select_best_candidate(candidates)
            selected = SelectedPair.from_candidate(
                issue_id,
                selected_candidate,
                selection_source="scoring",
                judge_model=args.judge_model,
                judge_exposure=args.exposure,
            )
            storage.save_candidates(issue_id, run_id, candidates)
            path = storage.save(selected)
            logger.info(
                "  %s: %s vs %s -> %s",
                issue_id,
                selected.solution_a.solution_id,
                selected.solution_b.solution_id,
                path,
            )
        except Exception as e:
            logger.error("  %s: FAILED - %s", issue_id, e)


def _list_solution_issue_ids(solutions_dir: Path) -> list[str]:
    from .storage import iter_solution_paths

    issue_ids = set()
    for folder in iter_solution_paths(solutions_dir):
        try:
            with open(folder / "solution.json", encoding="utf-8") as f:
                data = json.load(f)
            if issue_id := data.get("issue_id"):
                issue_ids.add(issue_id)
        except Exception as e:
            logger.warning("Skipping %s while listing issue ids: %s", folder, e)
    return sorted(issue_ids)


def _resolve_solution_path(solutions_dir: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = solutions_dir / path
    return path


def main() -> None:
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="routing",
        description="Routing preference research pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate
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

    # Judge
    judge_parser = subparsers.add_parser("judge", help="Judge solutions")
    judge_parser.add_argument(
        "--solutions-dir", "-s",
        type=Path,
        default=DEFAULT_SOLUTIONS_DIR,
        help=f"Directory containing solutions (default: {DEFAULT_SOLUTIONS_DIR})",
    )
    judge_parser.add_argument(
        "--judgments-dir",
        type=Path,
        default=DEFAULT_JUDGMENTS_DIR,
        help=f"Directory for judge outputs (default: {DEFAULT_JUDGMENTS_DIR})",
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

    # Select
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
        "--judgments-dir",
        type=Path,
        default=DEFAULT_JUDGMENTS_DIR,
        help=f"Directory containing judge outputs (default: {DEFAULT_JUDGMENTS_DIR})",
    )
    select_parser.add_argument(
        "--judge-model",
        default="openai/gpt-4o",
        help="Judge model whose scoring outputs should be used",
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
        "--selection-config",
        type=Path,
        default=None,
        help="Path to selection config JSON (default: configs/selection.json)",
    )
    select_parser.add_argument(
        "--max-average-gap",
        type=float,
        default=None,
        help=(
            "Maximum subjective-average gap for preferred pairs; if no pair "
            "matches, selection falls back to all pairs. Overrides config."
        ),
    )
    select_parser.add_argument(
        "--min-subscore-diversity",
        type=float,
        default=None,
        help=(
            "Minimum per-characteristic absolute score difference sum for "
            "preferred pairs. Overrides config."
        ),
    )
    select_parser.add_argument(
        "--global-balanced",
        action="store_true",
        help=(
            "Select one pair per issue jointly using the global balanced "
            "selector instead of independent per-issue selection"
        ),
    )
    select_parser.add_argument(
        "--selection-method",
        choices=["greedy", "cpsat"],
        default="greedy",
        help=(
            "Global selection backend to use with --global-balanced "
            "(default: greedy)"
        ),
    )
    select_parser.add_argument(
        "--selection-run-id",
        help=(
            "Run id for --global-balanced outputs; defaults to a deterministic "
            "id based on the selection method and judge source"
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
