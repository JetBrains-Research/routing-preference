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

1. Load all seven solutions and their scoring judgments.
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

The scoring exposure/version is configurable by the caller. Until the best judge variant is chosen, selection code should not hard-code one version.

## Output

Selected pairs are represented as:

```json
{
  "issue_id": "repo__name-123",
  "solution_a": "solution-folder-a",
  "solution_b": "solution-folder-b",
  "subjective_average_gap": 0.0,
  "subjective_profile_distance": 2.83,
  "objective_distance": 12.0,
  "scoring_exposure": "V1",
  "scoring_granularity": "all"
}
```

The storage helper writes one file per issue under `data/selections/`.
