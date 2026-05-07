"""Load scored solutions and save selected answer pairs."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .models import SelectedPair
from .selector import CHARACTERISTIC_ORDER, ScoredSolution, select_best_pair


def load_scored_solutions(
    solutions_dir: Path,
    issue_id: str,
    *,
    exposure: str,
    granularity: str = "all",
) -> list[ScoredSolution]:
    """Load scored solutions for one issue from stored solution folders."""
    scored = []

    for folder in sorted(solutions_dir.iterdir()):
        if not folder.is_dir() or not (folder / "solution.json").exists():
            continue

        solution = _load_json(folder / "solution.json")
        if solution.get("issue_id") != issue_id:
            continue

        judgment = _load_scoring_judgment(
            folder,
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
                solution_id=folder.name,
                scores=scores,
                objective_metrics=_load_objective_metrics(solution),
            )
        )

    return scored


def select_pair_for_issue(
    solutions_dir: Path,
    issue_id: str,
    *,
    exposure: str,
    expected_solutions: int = 7,
    max_average_gap: float = 0.75,
) -> SelectedPair:
    """Load scores for one issue and select its best survey pair."""
    scored = load_scored_solutions(
        solutions_dir,
        issue_id,
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
        scoring_exposure=exposure,
    )


class SelectionStorage:
    """Stores selected answer pairs under data/selections/."""

    def __init__(self, selections_dir: Path):
        self.selections_dir = selections_dir
        self.selections_dir.mkdir(parents=True, exist_ok=True)

    def save(self, selected_pair: SelectedPair) -> Path:
        path = self.selections_dir / f"{selected_pair.issue_id}.json"
        _atomic_write(path, json.dumps(asdict(selected_pair), indent=2))
        return path

    def load(self, issue_id: str) -> SelectedPair | None:
        path = self.selections_dir / f"{issue_id}.json"
        if not path.exists():
            return None
        return SelectedPair(**_load_json(path))


def _load_scoring_judgment(
    solution_folder: Path,
    *,
    exposure: str,
    granularity: str,
) -> dict | None:
    suffix = "all" if granularity == "all" else granularity
    path = solution_folder / "judgments" / f"{exposure}_scoring_{suffix}.json"
    if not path.exists():
        return None
    return _load_json(path)


def _load_objective_metrics(solution: dict) -> dict[str, float]:
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
