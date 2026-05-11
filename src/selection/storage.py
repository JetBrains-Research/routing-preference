"""Load scored solutions and save selected answer pairs."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from ..judge.storage import judge_run_id, slugify_judge_model
from ..storage import iter_solution_paths, solution_id_from_path
from .balanced import BalancedSelectionResult, IssueSelection, ScoredCandidate
from .models import SelectedPair, SelectedSolution
from .selector import (
    CHARACTERISTIC_ORDER,
    CandidatePair,
    ScoredSolution,
    generate_candidate_pairs,
    select_best_pair,
)


def load_scored_solutions(
    solutions_dir: Path,
    judgments_dir: Path,
    issue_id: str,
    *,
    judge_model: str,
    exposure: str,
    granularity: str = "all",
    characteristic_id: str | None = None,
) -> list[ScoredSolution]:
    """Load scored solutions for one issue from central judge outputs."""
    if granularity == "single" and not characteristic_id:
        raise ValueError("characteristic_id is required for single-granularity scoring")

    scored = []

    for folder in iter_solution_paths(solutions_dir, issue_id=issue_id):
        solution = _load_json(folder / "solution.json")
        solution_id = solution_id_from_path(folder)
        judgment = _load_scoring_judgment(
            judgments_dir,
            issue_id,
            solution_id,
            judge_model=judge_model,
            exposure=exposure,
            granularity=granularity,
            characteristic_id=characteristic_id,
        )
        if judgment is None:
            continue

        scores = {
            item["characteristic_id"]: float(item["value"])
            for item in judgment.get("scores", [])
            if item.get("characteristic_id") in CHARACTERISTIC_ORDER
        }

        scored.append(
            ScoredSolution(
                solution_id=solution_id,
                scores=scores,
                objective_metrics=_load_objective_metrics(folder, solution),
                model_slug=folder.parent.name,
                run_id=folder.name,
                relative_path=folder.relative_to(solutions_dir).as_posix(),
            )
        )

    return scored


def select_pair_for_issue(
    solutions_dir: Path,
    judgments_dir: Path,
    issue_id: str,
    *,
    judge_model: str,
    exposure: str,
    max_average_gap: float,
    min_subscore_diversity: float,
    expected_solutions: int = 7,
) -> SelectedPair:
    """Load scores for one issue and select its best survey pair."""
    scored = load_scored_solutions(
        solutions_dir,
        judgments_dir,
        issue_id,
        judge_model=judge_model,
        exposure=exposure,
        granularity="all",
    )
    if len(scored) != expected_solutions:
        raise ValueError(
            f"Expected {expected_solutions} scored solutions for {issue_id}, "
            f"found {len(scored)}"
        )

    candidate = select_best_pair(
        scored,
        max_average_gap=max_average_gap,
        min_subscore_diversity=min_subscore_diversity,
    )
    return SelectedPair.from_candidate(
        issue_id,
        candidate,
        selection_source="scoring",
        judge_model=judge_model,
        judge_exposure=exposure,
    )


class SelectionStorage:
    """Stores selected answer pairs under data/selections/<issue_id>/."""

    def __init__(self, selections_dir: Path):
        self.selections_dir = selections_dir
        self.selections_dir.mkdir(parents=True, exist_ok=True)

    def save(self, selected_pair: SelectedPair) -> Path:
        issue_dir = self.selections_dir / selected_pair.issue_id
        issue_dir.mkdir(parents=True, exist_ok=True)
        path = issue_dir / f"{selection_run_id(selected_pair)}.json"
        _atomic_write(path, json.dumps(asdict(selected_pair), indent=2))
        return path

    def save_candidates(
        self,
        issue_id: str,
        run_id: str,
        candidates: list[CandidatePair],
    ) -> Path:
        issue_dir = self.selections_dir / issue_id / "candidates"
        issue_dir.mkdir(parents=True, exist_ok=True)
        path = issue_dir / f"{run_id}.json"
        payload = {
            "issue_id": issue_id,
            "run_id": run_id,
            "candidate_count": len(candidates),
            "feasible_count": sum(1 for candidate in candidates if candidate.feasible),
            "candidates": [_candidate_payload(candidate) for candidate in candidates],
        }
        _atomic_write(path, json.dumps(payload, indent=2))
        return path

    def load(self, issue_id: str, run_id: str) -> SelectedPair | None:
        path = self.selections_dir / issue_id / f"{run_id}.json"
        if not path.exists():
            return None
        data = _load_json(path)
        data["solution_a"] = SelectedSolution(**data["solution_a"])
        data["solution_b"] = SelectedSolution(**data["solution_b"])
        return SelectedPair(**data)

    def save_global_run(
        self,
        run_id: str,
        result: BalancedSelectionResult,
        *,
        method: str = "greedy_balanced_v1",
    ) -> Path:
        """Save a global balanced selection run."""
        run_dir = self.selections_dir / "runs" / run_id
        candidates_dir = run_dir / "candidates"
        selected_dir = run_dir / "selected"
        candidates_dir.mkdir(parents=True, exist_ok=True)
        selected_dir.mkdir(parents=True, exist_ok=True)

        _atomic_write(
            run_dir / "config.json",
            json.dumps(asdict(result.config), indent=2),
        )

        selected_pairs = []
        for issue_id, issue_selection in sorted(result.selections.items()):
            candidates_path = candidates_dir / f"{issue_id}.json"
            selected_path = selected_dir / f"{issue_id}.json"
            _atomic_write(
                candidates_path,
                json.dumps(_issue_candidates_payload(issue_selection), indent=2),
            )
            selected_payload = _scored_candidate_payload(issue_selection.selected)
            selected_payload["issue_id"] = issue_id
            selected_payload["used_fallback"] = issue_selection.used_fallback
            _atomic_write(selected_path, json.dumps(selected_payload, indent=2))
            selected_pairs.append(
                {
                    "issue_id": issue_id,
                    "solution_ids": list(
                        issue_selection.selected.candidate.solution_ids
                    ),
                    "quality_band": issue_selection.selected.quality_band,
                    "used_fallback": issue_selection.used_fallback,
                }
            )

        summary = {
            "selection_run_id": run_id,
            "selection_method": method,
            "issue_count": len(result.selections),
            "model_usage": result.model_usage,
            "quality_band_usage": result.quality_band_usage,
            "selected_pairs": selected_pairs,
        }
        _atomic_write(run_dir / "summary.json", json.dumps(summary, indent=2))
        return run_dir


def selection_run_id(selected_pair: SelectedPair) -> str:
    """Build a filename-safe id for one selection source/run."""
    return selection_source_run_id(
        selected_pair.selection_source,
        selected_pair.judge_model,
        selected_pair.judge_exposure,
        selected_pair.judge_granularity,
        selected_pair.judge_characteristic,
    )


def selection_source_run_id(
    selection_source: str,
    judge_model: str,
    exposure: str,
    granularity: str = "all",
    characteristic: str | None = None,
) -> str:
    """Build the run id before a SelectedPair object exists."""
    characteristic_id = characteristic if granularity == "single" else "all"
    return "__".join(
        [
            selection_source,
            slugify_judge_model(judge_model),
            f"{exposure}_{characteristic_id}",
        ]
    )


def generate_candidates_for_issue(
    solutions_dir: Path,
    judgments_dir: Path,
    issue_id: str,
    *,
    judge_model: str,
    exposure: str,
    max_average_gap: float,
    min_subscore_diversity: float,
    expected_solutions: int = 7,
) -> list[CandidatePair]:
    """Load scores for one issue and generate all candidate pairs."""
    scored = load_scored_solutions(
        solutions_dir,
        judgments_dir,
        issue_id,
        judge_model=judge_model,
        exposure=exposure,
        granularity="all",
    )
    if len(scored) != expected_solutions:
        raise ValueError(
            f"Expected {expected_solutions} scored solutions for {issue_id}, "
            f"found {len(scored)}"
        )
    return generate_candidate_pairs(
        scored,
        max_average_gap=max_average_gap,
        min_subscore_diversity=min_subscore_diversity,
    )


def _candidate_payload(candidate: CandidatePair) -> dict:
    return {
        "solution_a": _scored_solution_payload(candidate.solution_a),
        "solution_b": _scored_solution_payload(candidate.solution_b),
        "solution_ids": list(candidate.solution_ids),
        "subjective_average": candidate.subjective_average,
        "subjective_average_gap": candidate.subjective_average_gap,
        "subjective_profile_distance": candidate.subjective_profile_distance,
        "subscore_diversity": candidate.subscore_diversity,
        "objective_distance": candidate.objective_distance,
        "local_score": candidate.local_score,
        "feasible": candidate.feasible,
    }


def _issue_candidates_payload(issue_selection: IssueSelection) -> dict:
    return {
        "issue_id": issue_selection.issue_id,
        "candidate_count": len(issue_selection.candidates),
        "used_fallback": issue_selection.used_fallback,
        "selected_solution_ids": list(
            issue_selection.selected.candidate.solution_ids
        ),
        "candidates": [
            _scored_candidate_payload(candidate)
            for candidate in issue_selection.candidates
        ],
    }


def _scored_candidate_payload(scored: ScoredCandidate) -> dict:
    payload = _candidate_payload(scored.candidate)
    payload.update(
        {
            "total_score": scored.total_score,
            "score_components": {
                "local": scored.local_component,
                "model_coverage": scored.model_coverage_component,
                "model_balance": scored.model_balance_component,
                "quality_band": scored.quality_band_component,
            },
            "quality_band": scored.quality_band,
        }
    )
    return payload


def _scored_solution_payload(solution: ScoredSolution) -> dict:
    return {
        "solution_id": solution.solution_id,
        "model_slug": solution.model_slug,
        "run_id": solution.run_id,
        "relative_path": solution.relative_path,
        "scores": dict(solution.scores),
        "subjective_average": solution.subjective_average,
    }


def _load_scoring_judgment(
    judgments_dir: Path,
    issue_id: str,
    solution_id: str,
    *,
    judge_model: str,
    exposure: str,
    granularity: str,
    characteristic_id: str | None,
) -> dict | None:
    path = (
        judgments_dir
        / issue_id
        / "scoring"
        / judge_run_id(judge_model, exposure, granularity, characteristic_id)
        / f"{solution_id}.json"
    )
    if not path.exists():
        return None
    return _load_json(path)


def _load_objective_metrics(solution_folder: Path, solution: dict) -> dict[str, float]:
    metrics_path = solution_folder / "objective_metrics.json"
    if metrics_path.exists():
        metrics = _load_json(metrics_path)
    else:
        metrics = solution.get("objective_metrics") or {}
    if not metrics and "duration_ms" in solution:
        metrics["completion_time_seconds"] = float(solution["duration_ms"]) / 1000
    return {
        key: float(value)
        for key, value in metrics.items()
        if isinstance(value, int | float)
    }


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _atomic_write(path: Path, content: str) -> None:
    temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    temp_path.replace(path)
