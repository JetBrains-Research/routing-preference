"""Optional CP-SAT backend for global balanced pair selection."""

from collections import Counter

from .balanced import (
    BalancedSelectionResult,
    IssueSelection,
    ScoredCandidate,
)
from .config import SelectionConfig
from .selector import CandidatePair


def select_balanced_pairs_cpsat(
    issue_candidates: dict[str, list[CandidatePair]],
    config: SelectionConfig,
) -> BalancedSelectionResult:
    """Select one pair per issue with an exact CP-SAT model."""
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise RuntimeError(
            "CP-SAT selection requires OR-Tools. Install `ortools` to use "
            "`routing select --selection-method cpsat`."
        ) from exc

    prepared = _prepare_candidates(issue_candidates, config)
    model_names = sorted(
        {
            model
            for scored_candidates in prepared.values()
            for scored in scored_candidates
            for model in _candidate_models(scored.candidate)
        }
    )
    if not model_names:
        raise ValueError("No candidate models available for CP-SAT selection")

    model = cp_model.CpModel()
    variables = {}
    for issue_id, scored_candidates in prepared.items():
        issue_vars = []
        for index, _ in enumerate(scored_candidates):
            var = model.NewBoolVar(f"x__{issue_id}__{index}")
            variables[(issue_id, index)] = var
            issue_vars.append(var)
        model.Add(sum(issue_vars) == 1)

    usage_vars = {}
    for model_name in model_names:
        usage = model.NewIntVar(0, 2 * len(prepared), f"usage__{model_name}")
        usage_vars[model_name] = usage
        model.Add(
            usage
            == sum(
                _candidate_model_count(scored.candidate, model_name)
                * variables[(issue_id, index)]
                for issue_id, scored_candidates in prepared.items()
                for index, scored in enumerate(scored_candidates)
            )
        )

    max_usage = model.NewIntVar(0, 2 * len(prepared), "max_usage")
    min_usage = model.NewIntVar(0, 2 * len(prepared), "min_usage")
    model.AddMaxEquality(max_usage, list(usage_vars.values()))
    model.AddMinEquality(min_usage, list(usage_vars.values()))
    spread = model.NewIntVar(0, 2 * len(prepared), "usage_spread")
    model.Add(spread == max_usage - min_usage)

    scaled_local = sum(
        int(round(scored.local_component * 1000)) * variables[(issue_id, index)]
        for issue_id, scored_candidates in prepared.items()
        for index, scored in enumerate(scored_candidates)
    )
    spread_penalty = int(round(config.model_balance_weight * 1000)) * spread
    model.Maximize(scaled_local - spread_penalty)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError("CP-SAT did not find a feasible selection")

    selections = {}
    model_usage: Counter[str] = Counter()
    quality_band_usage: Counter[str] = Counter()
    for issue_id, scored_candidates in prepared.items():
        selected = None
        for index, scored in enumerate(scored_candidates):
            if solver.Value(variables[(issue_id, index)]) == 1:
                selected = scored
                break
        if selected is None:
            raise ValueError(f"CP-SAT returned no selected pair for {issue_id}")
        for model_name in _candidate_models(selected.candidate):
            model_usage[model_name] += 1
        if selected.quality_band:
            quality_band_usage[selected.quality_band] += 1
        used_fallback = not any(
            candidate.feasible for candidate in issue_candidates[issue_id]
        )
        selections[issue_id] = IssueSelection(
            issue_id=issue_id,
            selected=selected,
            candidates=scored_candidates,
            used_fallback=used_fallback,
        )

    return BalancedSelectionResult(
        selections=selections,
        model_usage=dict(sorted(model_usage.items())),
        quality_band_usage=dict(sorted(quality_band_usage.items())),
        config=config,
    )


def _prepare_candidates(
    issue_candidates: dict[str, list[CandidatePair]],
    config: SelectionConfig,
) -> dict[str, list[ScoredCandidate]]:
    prepared = {}
    for issue_id, candidates in issue_candidates.items():
        if not candidates:
            raise ValueError(f"No candidates for issue: {issue_id}")
        pool = [candidate for candidate in candidates if candidate.feasible]
        if not pool:
            if config.fallback_if_no_feasible_pair != "best_local":
                raise ValueError(
                    f"No feasible candidates for {issue_id} and fallback is disabled"
                )
            pool = candidates
        prepared[issue_id] = [
            _static_score_candidate(candidate, config)
            for candidate in pool
        ]
    return prepared


def _static_score_candidate(
    candidate: CandidatePair,
    config: SelectionConfig,
) -> ScoredCandidate:
    quality_band = _quality_band(candidate.subjective_average, config)
    local_component = config.local_pair_quality_weight * candidate.local_score
    quality_band_component = 0.0
    return ScoredCandidate(
        candidate=candidate,
        total_score=local_component + quality_band_component,
        local_component=local_component,
        model_coverage_component=0.0,
        model_balance_component=0.0,
        quality_band_component=quality_band_component,
        quality_band=quality_band,
    )


def _candidate_models(candidate: CandidatePair) -> tuple[str, str]:
    models = (candidate.solution_a.model_slug, candidate.solution_b.model_slug)
    if not models[0] or not models[1]:
        raise ValueError(
            f"Candidate is missing model metadata: {candidate.solution_ids}"
        )
    return str(models[0]), str(models[1])


def _candidate_model_count(candidate: CandidatePair, model_name: str) -> int:
    return sum(
        1
        for candidate_model in _candidate_models(candidate)
        if candidate_model == model_name
    )


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
