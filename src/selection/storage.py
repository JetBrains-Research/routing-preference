"""Load scored solutions and save selected answer pairs."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from ..judge.storage import judge_run_id, slugify_judge_model
from ..storage import iter_solution_paths, solution_id_from_path
from .models import SelectedPair, SelectedSolution
from .selector import CHARACTERISTIC_ORDER, ScoredSolution, select_best_pair


def load_scored_solutions(
    solutions_dir: Path,
    judgments_dir: Path,
    issue_id: str,
    *,
    judge_model: str,
    exposure: str,
    granularity: str = "all",
) -> list[ScoredSolution]:
    """Load scored solutions for one issue from central judge outputs."""
    scored = []

    for folder in iter_solution_paths(solutions_dir):
        solution = _load_json(folder / "solution.json")
        if solution.get("issue_id") != issue_id:
            continue

        solution_id = solution_id_from_path(folder)
        judgment = _load_scoring_judgment(
            judgments_dir,
            issue_id,
            solution_id,
            judge_model=judge_model,
            exposure=exposure,
            granularity=granularity,
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
    expected_solutions: int = 7,
    max_average_gap: float = 0.75,
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

    candidate = select_best_pair(scored, max_average_gap=max_average_gap)
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

    def load(self, issue_id: str, run_id: str) -> SelectedPair | None:
        path = self.selections_dir / issue_id / f"{run_id}.json"
        if not path.exists():
            return None
        data = _load_json(path)
        data["solution_a"] = SelectedSolution(**data["solution_a"])
        data["solution_b"] = SelectedSolution(**data["solution_b"])
        return SelectedPair(**data)


def selection_run_id(selected_pair: SelectedPair) -> str:
    """Build a filename-safe id for one selection source/run."""
    characteristic = (
        selected_pair.judge_characteristic
        if selected_pair.judge_granularity == "single"
        else "all"
    )
    return "__".join(
        [
            selected_pair.selection_source,
            slugify_judge_model(selected_pair.judge_model),
            f"{selected_pair.judge_exposure}_{characteristic}",
        ]
    )


def _load_scoring_judgment(
    judgments_dir: Path,
    issue_id: str,
    solution_id: str,
    *,
    judge_model: str,
    exposure: str,
    granularity: str,
) -> dict | None:
    path = (
        judgments_dir
        / issue_id
        / "scoring"
        / judge_run_id(judge_model, exposure, granularity, None)
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
