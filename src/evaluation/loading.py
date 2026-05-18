"""Load scoring judgments for evaluation against manual scores."""

from __future__ import annotations

import json
from pathlib import Path

from src.evaluation.models import (
    EvaluationDataset,
    EvaluationSolution,
    ScoreSet,
    ScoringRun,
)
from src.judge.loader import CharacteristicLoader
from src.judge.storage import parse_judge_run_id
from src.storage import iter_solution_paths, solution_id_from_run_dir


def load_scoring_evaluation(
    *,
    solutions_dir: Path,
    judgments_dir: Path,
    judge_folders: list[Path | str],
    characteristics: tuple[str, ...] | None = None,
) -> EvaluationDataset:
    """Load manual and judge scores.

    Validation of the given judges before evaluation:
    - every issue in `solutions_dir` must have a manual scoring folder
    - every (issue,solution) must have exactly one manual scoring file
    - every requested judge run must have the needed scoring files
    - every requested judge run folder must contain all characteristics in one JSON
    """
    characteristics = characteristics or default_characteristics()
    scoring_runs = resolve_scoring_runs(
        judgments_dir=judgments_dir,
        judge_folders=judge_folders,
        characteristics=characteristics,
    )
    solutions = []
    issue_ids = _solution_issue_ids(solutions_dir)
    for issue_id in issue_ids:
        manual_dir = judgments_dir / issue_id / "scoring" / "manual"
        if not manual_dir.exists():
            raise ValueError(
                "Manual scoring folder does not exist for issue "
                f"{issue_id}: {manual_dir}"
            )
        if not any(manual_dir.glob("*.json")):
            raise ValueError(
                f"Manual scoring folder is empty for issue {issue_id}: {manual_dir}"
            )

        for solution_path in iter_solution_paths(solutions_dir, issue_id=issue_id):
            solution_id = solution_id_from_run_dir(solution_path)
            manual, solution_model, empty_solution = _load_manual_score(
                manual_dir=manual_dir,
                solution_path=solution_path,
                solution_id=solution_id,
                characteristics=characteristics,
            )
            judge_scores = {
                scoring_run.id: _load_judge_score_set(
                    judgments_dir=judgments_dir,
                    issue_id=issue_id,
                    solution_id=solution_id,
                    scoring_run=scoring_run,
                    characteristics=characteristics,
                )
                for scoring_run in scoring_runs
            }
            solutions.append(
                EvaluationSolution(
                    issue_id=issue_id,
                    solution_id=solution_id,
                    solution_model=solution_model,
                    empty_solution=empty_solution,
                    solution_path=solution_path,
                    manual=manual,
                    judge_scores=judge_scores,
                )
            )

    return EvaluationDataset(solutions=solutions)


def resolve_scoring_runs(
    *,
    judgments_dir: Path,
    judge_folders: list[Path | str],
    characteristics: tuple[str, ...] | None = None,
) -> list[ScoringRun]:
    """Resolve requested scoring run folders."""
    characteristics = characteristics or default_characteristics()
    folder_names = _requested_folder_names(judgments_dir, judge_folders)
    scoring_runs = {}

    for folder_name in folder_names:
        parsed = _parse_run_folder(folder_name, characteristics)
        if parsed["characteristic_id"] is not None:
            raise ValueError(
                "Legacy per-characteristic scoring folders are no longer supported: "
                f"{folder_name}. Use the combined _single folder instead."
            )
        run = ScoringRun(
            id=folder_name,
            judge_slug=str(parsed["judge_slug"]),
            exposure=str(parsed["exposure"]),
            granularity=str(parsed["granularity"]),
            folder=folder_name,
        )
        if run.id in scoring_runs:
            raise ValueError(
                f"Multiple scoring folders resolved to the same run id: {run.id}"
            )
        scoring_runs[run.id] = run

    return [scoring_runs[run_id] for run_id in sorted(scoring_runs)]


def _solution_issue_ids(solutions_dir: Path) -> list[str]:
    return sorted(
        path.name
        for path in solutions_dir.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def _requested_folder_names(
    judgments_dir: Path, judge_folders: list[Path | str]
) -> list[str]:
    folder_names = []
    if not judge_folders:
        for scoring_dir in sorted(judgments_dir.glob("*/scoring")):
            folder_names.extend(
                child.name
                for child in scoring_dir.iterdir()
                if child.is_dir() and child.name != "manual"
            )
    for folder in judge_folders:
        path = Path(folder)
        if not path.is_absolute():
            path = judgments_dir / path
        if path.name == "scoring":
            if not path.exists():
                raise ValueError(f"Scoring folder does not exist: {path}")
            folder_names.extend(
                child.name
                for child in path.iterdir()
                if child.is_dir() and child.name != "manual"
            )
        elif path.exists() and path.is_dir():
            folder_names.append(path.name)
        else:
            folder_names.append(Path(folder).name)
    if not folder_names:
        raise ValueError("At least one judge scoring folder must be provided")
    return sorted(set(folder_names))


def default_characteristics() -> tuple[str, ...]:
    """Return characteristic IDs from docs/judge/prompts.json."""
    return tuple(CharacteristicLoader().list_characteristics())


def _parse_run_folder(
    folder_name: str,
    characteristics: tuple[str, ...],
) -> dict[str, str | None]:
    return parse_judge_run_id(folder_name, characteristics)


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_manual_score(
    *,
    manual_dir: Path,
    solution_path: Path,
    solution_id: str,
    characteristics: tuple[str, ...],
) -> tuple[ScoreSet, str, bool]:
    model_slug = solution_path.parent.name
    candidates = [
        path
        for path in [
            manual_dir / f"{solution_id}.json",
            manual_dir / f"{model_slug}.json",
        ]
        if path.exists()
    ]
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple manual scoring files match {solution_id}: {candidates}"
        )
    if not candidates:
        raise ValueError(
            "Manual scoring file does not exist for solution "
            f"{solution_id} in {manual_dir}"
        )

    data = _load_json(candidates[0])
    scores = _scores_by_characteristic(
        data,
        path=candidates[0],
        expected_characteristics=characteristics,
    )
    return (
        ScoreSet(
            scores=scores,
            overall_score=float(data["overall_score"]),
            path=candidates[0],
        ),
        data["solution_model"],
        data["empty_solution"],
    )


def _load_judge_score_set(
    *,
    judgments_dir: Path,
    issue_id: str,
    solution_id: str,
    scoring_run: ScoringRun,
    characteristics: tuple[str, ...],
) -> ScoreSet:
    path = (
        judgments_dir
        / issue_id
        / "scoring"
        / scoring_run.folder
        / f"{solution_id}.json"
    )
    if not path.exists():
        raise ValueError(f"Missing judge scoring file: {path}")
    data = _load_json(path)
    return ScoreSet(
        scores=_scores_by_characteristic(
            data,
            path=path,
            expected_characteristics=characteristics,
        ),
        overall_score=float(data["overall_score"]),
        path=path,
    )


def _scores_by_characteristic(
    data: dict,
    *,
    path: Path,
    expected_characteristics: tuple[str, ...],
) -> dict[str, int]:
    scores = {}
    for score in data.get("scores", []):
        characteristic = score.get("characteristic_id")
        if characteristic in scores:
            raise ValueError(f"Duplicate score for {characteristic} in {path}")
        scores[characteristic] = score.get("value")

    missing = [char for char in expected_characteristics if char not in scores]
    extra = [char for char in scores if char not in expected_characteristics]
    if missing or extra:
        raise ValueError(
            f"Unexpected score characteristics in {path}: "
            f"missing={missing}, extra={extra}"
        )
    for characteristic, value in scores.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(
                f"Non-integer score for {characteristic} in {path}: {value!r}"
            )
    return scores
