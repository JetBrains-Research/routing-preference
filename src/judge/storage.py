"""Issue-first storage for scoring judgments and rankings."""

import json
import re
from dataclasses import asdict, fields
from pathlib import Path
from uuid import uuid4

from .models import (
    CharacteristicRanking,
    Ranking,
    RankingJudgment,
    Score,
    ScoringJudgment,
)

SCORING_JSON_KEY_ORDER = (
    "solution_folder",
    "issue_id",
    "solution_model",
    "judge_model",
    "empty_solution",
    "scores",
    "overall_score",
    "created_at",
    "exposure",
    "basis",
    "granularity",
    "score_scale",
)


def judgment_variant(
    exposure: str,
    granularity: str,
    characteristic_id: str | None,
) -> str:
    """Build the prompt/exposure variant suffix."""
    if granularity not in {"all", "single"}:
        raise ValueError(f"Unknown judgment granularity: {granularity}")
    return f"{exposure}_{granularity}"


def slugify_judge_model(judge_model: str) -> str:
    """Convert a judge model name to a filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", judge_model.strip())
    return slug.strip("_") or "unknown_model"


def slugify_group_id(group_id: str) -> str:
    """Convert a ranking group id to a filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", group_id.strip())
    return slug.strip("_") or "unknown_group"


def judge_run_id(
    judge_model: str,
    exposure: str,
    granularity: str,
    characteristic_id: str | None,
) -> str:
    """Build the shared run id used by scoring and ranking outputs."""
    return "__".join(
        [
            slugify_judge_model(judge_model),
            judgment_variant(exposure, granularity, characteristic_id),
        ]
    )


def parse_judge_run_id(
    run_id: str,
    characteristic_ids: list[str] | tuple[str, ...],
) -> dict[str, str | None]:
    """Parse a run id created by `judge_run_id`.

    Returns filesystem slugs, not the original unslugged judge model.
    """
    try:
        judge_slug, variant = run_id.rsplit("__", 1)
        exposure, suffix = variant.rsplit("_", 1)
    except ValueError as exc:
        raise ValueError(f"Not a recognized judge run id: {run_id}") from exc

    if suffix == "all":
        return {
            "judge_slug": judge_slug,
            "exposure": exposure,
            "granularity": "all",
            "characteristic_id": None,
        }
    if suffix == "single":
        return {
            "judge_slug": judge_slug,
            "exposure": exposure,
            "granularity": "single",
            "characteristic_id": None,
        }
    if suffix in characteristic_ids:
        return {
            "judge_slug": judge_slug,
            "exposure": exposure,
            "granularity": "single",
            "characteristic_id": suffix,
        }
    raise ValueError(f"Not a recognized judge run id: {run_id}")


def _atomic_write(path: Path, content: str) -> None:
    temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    temp_path.replace(path)


def _ordered_scoring_judgment_dict(judgment: ScoringJudgment) -> dict:
    data = asdict(judgment)
    ordered = {key: data[key] for key in SCORING_JSON_KEY_ORDER if key in data}
    ordered.update({key: value for key, value in data.items() if key not in ordered})
    return ordered


class ScoringStorage:
    """Per-solution scores stored under data/judgments/<issue_id>/scoring/."""

    def __init__(self, judgments_dir: Path):
        self.judgments_dir = judgments_dir
        self.judgments_dir.mkdir(parents=True, exist_ok=True)

    def save(self, judgment: ScoringJudgment) -> Path:
        run_dir = (
            self.judgments_dir
            / judgment.issue_id
            / "scoring"
            / judge_run_id(
                judgment.judge_model,
                judgment.exposure,
                judgment.granularity,
                None,
            )
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{judgment.solution_folder}.json"
        _atomic_write(
            path,
            json.dumps(
                _ordered_scoring_judgment_dict(judgment),
                indent=2,
                ensure_ascii=False,
            ),
        )
        return path

    def load(
        self,
        issue_id: str,
        solution_folder: str,
        judge_model: str,
        exposure: str,
        granularity: str,
    ) -> ScoringJudgment | None:
        path = (
            self.judgments_dir
            / issue_id
            / "scoring"
            / judge_run_id(judge_model, exposure, granularity, None)
            / f"{solution_folder}.json"
        )
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Drop fields removed from the dataclass so old files still load.
        known = {f.name for f in fields(ScoringJudgment)}
        data = {k: v for k, v in data.items() if k in known}
        data["scores"] = [Score(**s) for s in data["scores"]]
        if data.get("score_scale"):
            data["score_scale"] = tuple(data["score_scale"])
        return ScoringJudgment(**data)

    def has_judgment(
        self,
        issue_id: str,
        solution_folder: str,
        judge_model: str,
        exposure: str,
        granularity: str,
    ) -> bool:
        return (
            self.load(
                issue_id,
                solution_folder,
                judge_model,
                exposure,
                granularity,
            )
            is not None
        )


class RankingStorage:
    """Rankings stored under data/judgments/<issue_id>/ranking/<group_id>/."""

    def __init__(self, judgments_dir: Path):
        self.judgments_dir = judgments_dir
        self.judgments_dir.mkdir(parents=True, exist_ok=True)

    def save(self, judgment: RankingJudgment) -> Path:
        ranking_dir = (
            self.judgments_dir
            / judgment.issue_id
            / "ranking"
            / slugify_group_id(judgment.group_id)
        )
        ranking_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            judge_run_id(
                judgment.judge_model,
                judgment.exposure,
                judgment.granularity,
                None,
            )
            + ".json"
        )
        path = ranking_dir / filename
        _atomic_write(path, json.dumps(asdict(judgment), indent=2, ensure_ascii=False))
        return path

    def load(
        self,
        issue_id: str,
        group_id: str,
        judge_model: str,
        exposure: str,
        granularity: str,
    ) -> RankingJudgment | None:
        filename = judge_run_id(judge_model, exposure, granularity, None) + ".json"
        path = (
            self.judgments_dir
            / issue_id
            / "ranking"
            / slugify_group_id(group_id)
            / filename
        )
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Drop fields removed from the dataclass so old files still load.
        known = {f.name for f in fields(RankingJudgment)}
        data = {k: v for k, v in data.items() if k in known}
        data["rankings"] = [
            CharacteristicRanking(
                characteristic_id=cr["characteristic_id"],
                rankings=[Ranking(**r) for r in cr["rankings"]],
            )
            for cr in data["rankings"]
        ]
        return RankingJudgment(**data)

    def has_ranking(
        self,
        issue_id: str,
        group_id: str,
        judge_model: str,
        exposure: str,
        granularity: str,
    ) -> bool:
        return (
            self.load(
                issue_id,
                group_id,
                judge_model,
                exposure,
                granularity,
            )
            is not None
        )
