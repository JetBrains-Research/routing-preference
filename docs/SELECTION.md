# Answer Selection

Answer selection chooses which two generated solutions for an issue are shown in the user survey.

Each issue is expected to have seven generated solutions, one from each model. Selection currently uses only subjective scoring judgments.

## Inputs

For each solution, answer selection needs scores for the four subjective characteristics:

- Intent Understanding
- Functional Correctness
- Scope Adherence
- Code Quality

Objective characteristics are not used as primary selection criteria:

- Completion Time
- Step Count

They may be used as tie-breakers and should be shown in the survey.

## Selection Rule

For every issue:

1. Load all seven solutions and their scoring judgments for the selected judge model.
2. Build a subjective score vector for each solution:

   ```text
   [intent, correctness, scope, quality]
   ```

3. Compute each solution's subjective average and centered score profile.
4. Generate all possible solution pairs.
5. Keep pairs whose subjective averages are close enough.
6. Select the remaining pair with the largest subjective profile difference.

Profile difference is computed after subtracting each solution's own subjective average from its scores. This emphasizes different characteristic tradeoffs rather than simply choosing one uniformly strong solution and one uniformly weak solution.

The default maximum subjective-average gap is `0.75` on the 1-5 score scale. If no pair is within that gap, selection falls back to all pairs.

## Tie-Breakers

When pairs have the same subjective profile difference, prefer:

1. Smaller subjective-average gap.
2. Larger objective metric distance, if objective metrics are available.
3. Deterministic ordering by solution id.

The deterministic final tie-breaker keeps selection reproducible.

## Current Scope

Only scoring judgments are used. Ranking judgments are intentionally out of scope for the first implementation.

Scoring judgments are read from the issue-first judge output tree:

```text
data/judgments/<issue_id>/scoring/<judge_model_slug>__<exposure>_<all|characteristic>/<solution_id>.json
```

`solution_id` is the generated solution model slug plus the run id:

```text
<solution_model_slug>__<run_id>
```

The scoring exposure/version is configurable by the caller. Until the best judge variant is chosen, selection code should not hard-code one version.

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

The storage helper writes one file per issue and selection source:

```text
data/selections/<issue_id>/<selection_source>__<judge_model_slug>__<exposure>_<all|characteristic>.json
```

For example:

```text
data/selections/repo__name-123/scoring__openai_gpt-4o__V1_all.json
```
