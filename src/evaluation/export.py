"""Export manual-vs-judge scoring comparisons."""

from __future__ import annotations

import csv
import random
from pathlib import Path

from src.evaluation.loading import (
    default_characteristics,
    load_scoring_evaluation,
    resolve_scoring_runs,
)
from src.evaluation.models import EvaluationExportResult

CHARACTERISTIC_CSV_COLUMNS = (
    "judge_run_id",
    "judge_slug",
    "exposure",
    "granularity",
    "n",
    "issue_count",
    "mean_manual_score",
    "mean_judge_score",
    "mean_signed_error",
    "mean_absolute_error",
    "closeness_percent",
    "mae_ci_lower",
    "mae_ci_upper",
    "closeness_ci_lower",
    "closeness_ci_upper",
    "macro_f1",
    "exact_match_rate",
    "within_1_rate",
    "over_score_rate",
    "under_score_rate",
)


def build_scoring_evaluation_rows(
    *,
    solutions_dir: Path,
    judgments_dir: Path,
    judge_folders: list[Path | str],
    output_path: Path,
    characteristics: tuple[str, ...] | None = None,
) -> tuple[list[dict], EvaluationExportResult]:
    """Build strict long-form manual-vs-judge scoring rows.

    This rejects any issue or solution in `solutions_dir` that does not have
    matching manual scoring.
    """
    characteristics = characteristics or default_characteristics()
    scoring_runs = resolve_scoring_runs(
        judgments_dir=judgments_dir,
        judge_folders=judge_folders,
        characteristics=characteristics,
    )
    runs_by_id = {run.id: run for run in scoring_runs}
    dataset = load_scoring_evaluation(
        solutions_dir=solutions_dir,
        judgments_dir=judgments_dir,
        judge_folders=judge_folders,
        characteristics=characteristics,
    )

    rows = []
    for solution in dataset.solutions:
        for run_id, judge_score_set in sorted(solution.judge_scores.items()):
            run = runs_by_id[run_id]
            for characteristic in characteristics:
                manual_score = solution.manual.scores[characteristic]
                judge_score = judge_score_set.scores[characteristic]
                signed_error = judge_score - manual_score
                rows.append(
                    {
                        "issue_id": solution.issue_id,
                        "solution_id": solution.solution_id,
                        "solution_model": solution.solution_model,
                        "empty_solution": solution.empty_solution,
                        "judge_run_id": run.id,
                        "judge_slug": run.judge_slug,
                        "exposure": run.exposure,
                        "granularity": run.granularity,
                        "characteristic": characteristic,
                        "manual_score": manual_score,
                        "judge_score": judge_score,
                        "signed_error": signed_error,
                        "absolute_error": abs(signed_error),
                        "manual_path": solution.manual.path,
                        "judge_path": judge_score_set.path,
                    }
                )

    issue_ids = {solution.issue_id for solution in dataset.solutions}
    result = EvaluationExportResult(
        path=output_path,
        row_count=len(rows),
        solution_count=len(dataset.solutions),
        issue_count=len(issue_ids),
    )
    return rows, result


def write_scoring_characteristic_comparison_csvs(
    *,
    rows: list[dict],
    output_dir: Path,
    characteristics: tuple[str, ...],
    bootstrap_samples: int = 5000,
    bootstrap_seed: int = 0,
) -> dict[str, Path]:
    """Write one per-judge evaluation CSV per subjective characteristic."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for characteristic in characteristics:
        path = output_dir / f"{characteristic}_comparison.csv"
        characteristic_rows = summarize_characteristic_rows(
            rows=[row for row in rows if row["characteristic"] == characteristic],
            bootstrap_samples=bootstrap_samples,
            bootstrap_seed=bootstrap_seed,
        )
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CHARACTERISTIC_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(characteristic_rows)
        paths[characteristic] = path
    return paths


def summarize_characteristic_rows(
    *,
    rows: list[dict],
    bootstrap_samples: int = 5000,
    bootstrap_seed: int = 0,
) -> list[dict]:
    """Summarize one characteristic as one row per judge run."""
    by_judge = {}
    for row in rows:
        by_judge.setdefault(row["judge_run_id"], []).append(row)

    summaries = []
    for judge_run_id in sorted(by_judge):
        judge_rows = by_judge[judge_run_id]
        first = judge_rows[0]
        mae_ci_lower, mae_ci_upper = _cluster_bootstrap_mae_ci(
            judge_rows,
            samples=bootstrap_samples,
            seed=f"{bootstrap_seed}:{judge_run_id}",
        )
        signed_errors = [float(row["signed_error"]) for row in judge_rows]
        absolute_errors = [float(row["absolute_error"]) for row in judge_rows]
        manual_scores = [float(row["manual_score"]) for row in judge_rows]
        judge_scores = [float(row["judge_score"]) for row in judge_rows]
        issue_ids = {row["issue_id"] for row in judge_rows}
        mean_absolute_error = _mean(absolute_errors)
        summaries.append(
            {
                "judge_run_id": judge_run_id,
                "judge_slug": first["judge_slug"],
                "exposure": first["exposure"],
                "granularity": first["granularity"],
                "n": len(judge_rows),
                "issue_count": len(issue_ids),
                "mean_manual_score": _mean(manual_scores),
                "mean_judge_score": _mean(judge_scores),
                "mean_signed_error": _mean(signed_errors),
                "mean_absolute_error": mean_absolute_error,
                "closeness_percent": _closeness_percent(mean_absolute_error),
                "mae_ci_lower": mae_ci_lower,
                "mae_ci_upper": mae_ci_upper,
                "closeness_ci_lower": _closeness_percent(mae_ci_upper),
                "closeness_ci_upper": _closeness_percent(mae_ci_lower),
                "macro_f1": _macro_f1(judge_rows),
                "exact_match_rate": _rate(error == 0 for error in signed_errors),
                "within_1_rate": _rate(abs(error) <= 1 for error in signed_errors),
                "over_score_rate": _rate(error > 0 for error in signed_errors),
                "under_score_rate": _rate(error < 0 for error in signed_errors),
            }
        )
    return summaries


def _cluster_bootstrap_mae_ci(
    rows: list[dict],
    *,
    samples: int,
    seed: int | str,
) -> tuple[float, float]:
    by_issue = {}
    for row in rows:
        by_issue.setdefault(row["issue_id"], []).append(row)
    issue_ids = sorted(by_issue)
    if not issue_ids:
        return 0.0, 0.0

    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        sampled_rows = []
        for _ in issue_ids:
            sampled_issue = rng.choice(issue_ids)
            sampled_rows.extend(by_issue[sampled_issue])
        estimates.append(_mean([float(row["absolute_error"]) for row in sampled_rows]))
    estimates.sort()
    return _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    position = quantile * (len(values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)
    weight = position - lower_index
    return values[lower_index] * (1 - weight) + values[upper_index] * weight


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _closeness_percent(mean_absolute_error: float) -> float:
    return 100 * (1 - mean_absolute_error / 4)


def _macro_f1(rows: list[dict]) -> float:
    f1_values = []
    for score_class in range(1, 6):
        true_positive = sum(
            1
            for row in rows
            if row["manual_score"] == score_class and row["judge_score"] == score_class
        )
        false_positive = sum(
            1
            for row in rows
            if row["manual_score"] != score_class and row["judge_score"] == score_class
        )
        false_negative = sum(
            1
            for row in rows
            if row["manual_score"] == score_class and row["judge_score"] != score_class
        )
        denominator = 2 * true_positive + false_positive + false_negative
        f1_values.append(0.0 if denominator == 0 else (2 * true_positive) / denominator)
    return _mean(f1_values)


def _rate(values) -> float:
    values = list(values)
    return sum(1 for value in values if value) / len(values) if values else 0.0
