# Answer Selection

Answer selection chooses which two generated solutions for an issue are shown in the user survey.

Each issue is expected to have seven generated solutions, one from each model.
Selection currently uses subjective scoring judgments.

## Goal

The survey should compare two answers that are similar in overall quality but different in their characteristic profile.

For each solution, selection uses the four subjective characteristics:

- Intent Understanding
- Functional Correctness
- Scope Adherence
- Code Quality

Objective characteristics are not primary selection criteria:

- Completion Time
- Step Count

The Objective characteristics will be displayed to the user in the survey only.

## Problem Framing

Selection is a two-level problem:

1. **Local candidate generation**: for each issue, enumerate all solution pairs and keep pairs that satisfy the per-issue comparison criteria.
2. **Global balanced selection**: across all issues, choose one pair per issue while balancing model coverage in the final survey set.

The framing is:

```text
Global balanced multiple-choice pair selection
```

Each issue is a group. Each feasible pair for that issue is a candidate choice.
The selector chooses exactly one candidate per issue while optimizing both local pair quality and global coverage constraints.

## Local Candidates

For each issue:

1. Load all seven solutions and their judgments for the selected judge model, exposure, and granularity.
2. Build a subjective score vector for each solution:

   ```text
   [intent, correctness, scope, quality]
   ```

3. Enumerate all 21 unordered solution pairs.
4. Compute candidate metrics for each pair.
5. Mark each pair as feasible or infeasible.

Candidate metrics:

```text
mean_a = mean(scores_a)
mean_b = mean(scores_b)

average_gap = abs(mean_a - mean_b)
profile_distance = distance(center(scores_a), center(scores_b))
subscore_diversity = sum(abs(scores_a[c] - scores_b[c]) for c in characteristics)
```

`center(scores)` subtracts the solution's own average from each characteristic score.
This emphasizes different characteristic tradeoffs rather than simply selecting one uniformly strong answer and one uniformly weak answer.

A candidate is feasible when:

```text
average_gap <= max_average_gap
subscore_diversity >= min_subscore_diversity
```

If no pair is feasible, the selector may fall back to the best local pair.

## Quality Bands

The selector must not prefer only middle-quality pairs by default.

Pairs where both answers are bad, both are medium, or both are good are valid if they satisfy the local candidate criteria.
This is intentional: the survey should cover tradeoffs across the quality spectrum.

Quality bands are optional diagnostics and optional global balancing targets:

```text
bad:    pair_mean < low_threshold
medium: low_threshold <= pair_mean < high_threshold
good:   pair_mean >= high_threshold
```

Quality-band balancing should be configurable.
`quality_bands` may be omitted when `quality_band_balance_weight` is `0`.
If `quality_band_balance_weight` is greater than `0`, quality bands must be
defined.


## Global Selection

For small calibration sets, per-issue local selection is acceptable.

With around 1000 issues and seven models, selecting one pair per issue creates 2000 model appearances in the survey.
The goal is to have balanced appearances across all models.

The global selector should choose one candidate per issue while trading off:

- local pair quality
- model coverage across the whole survey set
- model-pair diversity
- optional quality-band coverage

This is implemented first as a greedy balanced selector. An optional CP-SAT
backend is available for exact optimization when OR-Tools is installed.

## Greedy Balanced Selector

The greedy implementation is deterministic and inspectable:

1. Generate feasible candidates for every issue.
2. Sort issues by fewest feasible candidates first.
3. For each issue, score candidates using:

   ```text
   total_score =
      local_pair_quality_weight   * local_score
    + model_coverage_weight       * model_coverage_bonus
    + model_balance_weight        * model_balance_bonus
    + quality_band_balance_weight * quality_band_bonus
   ```

4. Select the highest-scoring candidate for that issue.
5. Update global usage counts.
6. Store all candidate metrics and the reason for the selected pair.

This is not guaranteed to be globally optimal, but it is simple, deterministic, and easy to debug.

## Exact Optimizer

The CP-SAT backend models selection as an exact optimization problem:

Decision variable:

```text
x[i,p] = 1 if candidate pair p is selected for issue i
```

Required constraint:

```text
for every issue i:
    sum_p x[i,p] = 1
```

Model usage:

```text
usage[m] = sum_i,p uses_model[p,m] * x[i,p]
```

Optional hard constraints:

```text
min_usage[m] <= usage[m] <= max_usage[m]
```

Objective:

```text
maximize local_pair_quality - model_imbalance_penalty
```

This is a multiple-choice assignment problem with balancing constraints.

## Configuration

Selection is parameterized by `configs/selection.json`:

```json
{
  "max_average_gap": 0.75,
  "min_subscore_diversity": 0.0,
  "local_pair_quality_weight": 1.0,
  "model_coverage_weight": 0.4,
  "model_balance_weight": 0.3,
  "quality_band_balance_weight": 0.0,
  "fallback_if_no_feasible_pair": "best_local",
  "quality_bands": {
    "bad": [1.0, 2.5],
    "medium": [2.5, 3.75],
    "good": [3.75, 5.0]
  }
}
```

The per-issue selector uses `max_average_gap` and `min_subscore_diversity`.
The global balanced selector also uses the model and quality-band weights.
Selection outputs record the effective config used for each global run.

## Inputs

Scoring judgments are read from the issue-first judge output tree:

```text
data/judgments/<issue_id>/scoring/<judge_model_slug>__<exposure>_<all|characteristic>/<solution_id>.json
```

`solution_id` is the generated solution model slug plus the run id:

```text
<solution_model_slug>__<run_id>
```

The scoring exposure/version is configurable by the caller.

## Output

Selected pairs are represented as:

```json
{
  "issue_id": "repo__name-123",
  "solution_a": {
    "solution_id": "openai_gpt-4o-mini__20260507_131500_123456",
    "model_slug": "openai_gpt-4o-mini",
    "run_id": "20260507_131500_123456",
    "relative_path": "repo__name-123/openai_gpt-4o-mini/20260507_131500_123456"
  },
  "solution_b": {
    "solution_id": "anthropic_claude-sonnet__20260507_132010_654321",
    "model_slug": "anthropic_claude-sonnet",
    "run_id": "20260507_132010_654321",
    "relative_path": "repo__name-123/anthropic_claude-sonnet/20260507_132010_654321"
  },
  "subjective_average_gap": 0.0,
  "subjective_profile_distance": 2.83,
  "objective_distance": 12.0,
  "selection_source": "scoring",
  "judge_model": "openai/gpt-4o",
  "judge_exposure": "V1",
  "judge_granularity": "all",
  "judge_characteristic": null
}
```

Global balanced selection writes a run-level output:

```text
data/selections/runs/<selection_run_id>/
  config.json
  summary.json
  candidates/<issue_id>.json
  selected/<issue_id>.json
```

Per-issue candidate diagnostics store all 21 candidate pairs, including
feasibility flags, metrics, and local score. Run-level candidate diagnostics
store the scored pool used by the global selector, including global score
components and quality-band assignment.

## Current Storage

The current storage helper writes one file per issue and selection source:

```text
data/selections/<issue_id>/<selection_source>__<judge_model_slug>__<exposure>_<all|characteristic>.json
```

For example:

```text
data/selections/repo__name-123/scoring__openai_gpt-4o__V1_all.json
```

Run global balanced selection with:

```bash
uv run routing select --global-balanced
```

The command also accepts:

```bash
uv run routing select --global-balanced --selection-method cpsat
```

The CP-SAT backend is optional and requires OR-Tools. The default `greedy`
backend has no extra dependency and is the recommended first pass for the 15
issue calibration set. Use `--selection-run-id` when a stable explicit run id is
needed.
