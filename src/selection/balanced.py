"""Greedy global balanced pair selection."""

from collections import Counter
from dataclasses import dataclass

from .config import SelectionConfig
from .selector import CandidatePair


@dataclass(frozen=True)
class ScoredCandidate:
    """A candidate with its global greedy score components."""

    candidate: CandidatePair
    total_score: float
    local_component: float
    model_coverage_component: float
    model_balance_component: float
    quality_band_component: float
    quality_band: str | None


@dataclass(frozen=True)
class IssueSelection:
    """Selected candidate for one issue."""

    issue_id: str
    selected: ScoredCandidate
    candidates: list[ScoredCandidate]
    used_fallback: bool


@dataclass(frozen=True)
class BalancedSelectionResult:
    """Global greedy selection result."""

    selections: dict[str, IssueSelection]
    model_usage: dict[str, int]
    quality_band_usage: dict[str, int]
    config: SelectionConfig


def select_balanced_pairs(
    issue_candidates: dict[str, list[CandidatePair]],
    config: SelectionConfig,
) -> BalancedSelectionResult:
    """Select one pair per issue while preferring underrepresented models."""
    model_usage: Counter[str] = Counter()
    quality_band_usage: Counter[str] = Counter()
    selections: dict[str, IssueSelection] = {}

    ordered_issues = sorted(
        issue_candidates,
        key=lambda issue_id: (
            _candidate_pool_size(issue_candidates[issue_id]),
            issue_id,
        ),
    )

    for issue_id in ordered_issues:
        candidates = issue_candidates[issue_id]
        if not candidates:
            raise ValueError(f"No candidates for issue: {issue_id}")

        pool = [candidate for candidate in candidates if candidate.feasible]
        used_fallback = False
        if not pool:
            if config.fallback_if_no_feasible_pair != "best_local":
                raise ValueError(
                    f"No feasible candidates for {issue_id} and fallback is disabled"
                )
            pool = candidates
            used_fallback = True

        scored = [
            _score_candidate(
                candidate,
                config,
                model_usage=model_usage,
                quality_band_usage=quality_band_usage,
            )
            for candidate in pool
        ]
        selected = sorted(scored, key=_scored_candidate_sort_key)[0]
        _update_usage(model_usage, selected.candidate)
        if selected.quality_band:
            quality_band_usage[selected.quality_band] += 1
        selections[issue_id] = IssueSelection(
            issue_id=issue_id,
            selected=selected,
            candidates=scored,
            used_fallback=used_fallback,
        )

    return BalancedSelectionResult(
        selections=selections,
        model_usage=dict(sorted(model_usage.items())),
        quality_band_usage=dict(sorted(quality_band_usage.items())),
        config=config,
    )


def _candidate_pool_size(candidates: list[CandidatePair]) -> int:
    feasible_count = sum(1 for candidate in candidates if candidate.feasible)
    return feasible_count or len(candidates)


def _score_candidate(
    candidate: CandidatePair,
    config: SelectionConfig,
    *,
    model_usage: Counter[str],
    quality_band_usage: Counter[str],
) -> ScoredCandidate:
    models = _candidate_models(candidate)
    quality_band = _quality_band(candidate.subjective_average, config)

    local_component = config.local_pair_quality_weight * candidate.local_score
    model_coverage_component = config.model_coverage_weight * sum(
        1 for model in models if model_usage[model] == 0
    )
    model_balance_component = config.model_balance_weight * (
        -sum(model_usage[model] for model in models)
    )
    quality_band_component = 0.0
    if quality_band is not None:
        quality_band_component = config.quality_band_balance_weight * (
            -quality_band_usage[quality_band]
        )

    return ScoredCandidate(
        candidate=candidate,
        total_score=(
            local_component
            + model_coverage_component
            + model_balance_component
            + quality_band_component
        ),
        local_component=local_component,
        model_coverage_component=model_coverage_component,
        model_balance_component=model_balance_component,
        quality_band_component=quality_band_component,
        quality_band=quality_band,
    )


def _scored_candidate_sort_key(scored: ScoredCandidate) -> tuple:
    candidate = scored.candidate
    return (
        -round(scored.total_score, 12),
        -round(candidate.local_score, 12),
        round(candidate.subjective_average_gap, 12),
        -round(candidate.objective_distance, 12),
        candidate.solution_ids,
    )


def _candidate_models(candidate: CandidatePair) -> tuple[str, str]:
    models = (candidate.solution_a.model_slug, candidate.solution_b.model_slug)
    if not models[0] or not models[1]:
        raise ValueError(
            f"Candidate is missing model metadata: {candidate.solution_ids}"
        )
    return str(models[0]), str(models[1])


def _update_usage(model_usage: Counter[str], candidate: CandidatePair) -> None:
    for model in _candidate_models(candidate):
        model_usage[model] += 1


def _quality_band(score: float, config: SelectionConfig) -> str | None:
    if not config.quality_bands:
        return None
    for name, (lower, upper) in config.quality_bands.items():
        if lower <= score < upper:
            return name
    max_band = max(config.quality_bands.items(), key=lambda item: item[1][1])
    if score == max_band[1][1]:
        return max_band[0]
    return None
