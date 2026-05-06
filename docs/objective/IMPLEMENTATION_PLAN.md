# Objective Metrics Implementation Plan

This plan covers implementation of the two objective characteristics:

- `completion_time`
- `step_count`

These metrics are measured by code during solution generation. They do not use LLM judge prompts.

Status: implemented for newly generated solutions.

## Goals

Store objective metrics explicitly with each generated solution so later pair selection and analysis do not need to infer them from raw trajectory data.

Keep existing solution data backward compatible where possible. Existing `duration_ms` can remain during transition, but new code should expose clearer metric fields.

## Data Model

Add an objective metrics structure to the solution model.

Recommended shape:

```json
{
  "objective_metrics": {
    "completion_time_seconds": 4.95,
    "step_count": 1,
    "raw_action_count": 2,
    "model_call_count": 2
  }
}
```

Field definitions:

| Field | Description |
|-------|-------------|
| `completion_time_seconds` | Main `completion_time` characteristic value. |
| `step_count` | Main `step_count` characteristic value, excluding submission command. |
| `raw_action_count` | All assistant action turns, including submission command. Diagnostic only. |
| `model_call_count` | Number of model calls recorded by mini-swe-agent. Diagnostic only. |

Keep `duration_ms` for compatibility until downstream code is updated.

## Completion Time

Current `duration_ms` is close to the desired boundary:

- starts before `_run_agent()`
- includes mini-swe-agent execution
- includes final `git diff`
- excludes clone and checkout

Implementation steps:

1. Switch timing from `datetime.now()` deltas to `time.monotonic()` for elapsed duration.
2. Measure from immediately before `_run_agent()` starts until after `_run_agent()` returns.
3. Ensure `_run_agent()` continues to include final `git diff` capture.
4. Store seconds as a float in `objective_metrics.completion_time_seconds`.
5. Continue storing integer `duration_ms` as derived compatibility data.

## Step Count

Derive step count from the serialized mini-swe-agent trajectory.

Implementation steps:

1. Add a small helper that reads `trajectory["messages"]`.
2. Count assistant messages with `extra.actions`.
3. Count all such action turns as `raw_action_count`.
4. Exclude actions where every command is the final submission command:

   ```bash
   echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
   ```

5. Store the filtered count as `objective_metrics.step_count`.
6. Use `trajectory["info"]["model_stats"]["api_calls"]` for `model_call_count` when present.

Important interpretation:

- A single bash command with multiple shell operations still counts as one step.
- Format-error turns do not count unless they include an executable action.
- Exit messages do not count.
- The final submission command is protocol overhead and does not count toward `step_count`.

## Code Placement

Recommended new module:

```text
src/objective/
  __init__.py
  metrics.py
```

Responsibilities:

- `compute_objective_metrics(trajectory, completion_time_seconds) -> ObjectiveMetrics`
- helper for detecting submission commands
- helper for counting action turns

Keep this separate from `src/judge/` because objective metrics are not LLM judgments.

## Storage

Update:

- `src/models.py`
- `src/generator.py`
- `src/storage.py` only if needed for serialization compatibility

The generated `solution.json` should contain the new `objective_metrics` field.

Example:

```json
{
  "issue_id": "Textualize__rich-4050",
  "model": "openai/gpt-4o-mini",
  "provider": "openai",
  "diff": "...",
  "trajectory": {},
  "duration_ms": 4950,
  "objective_metrics": {
    "completion_time_seconds": 4.95,
    "step_count": 1,
    "raw_action_count": 2,
    "model_call_count": 2
  },
  "created_at": "..."
}
```

## Tests

Add focused unit tests for metric extraction.

Recommended tests:

1. Counts one normal action and excludes submit command.
2. Counts multiple normal actions.
3. Handles missing `messages`.
4. Handles missing `model_stats`.
5. Does not count exit messages.
6. Treats a compound bash command as one step.

Use the existing sample solution trajectory as a fixture or create minimal synthetic trajectories.

## Migration / Backfill

Existing solution folders do not have `objective_metrics`.

Backfill can be added later as a script:

```text
scripts/backfill_objective_metrics.py
```

Backfill limitation:

- `step_count`, `raw_action_count`, and `model_call_count` can be reconstructed from existing trajectories.
- `completion_time_seconds` can only be derived from existing `duration_ms`; this is acceptable for current data because `duration_ms` already follows the intended boundary closely.

## Open Decisions

1. Whether `objective_metrics` should eventually be stored in a separate file, such as `objective_metrics.json`, for easier partial recomputation.
2. Whether to record component timings, such as model wait time and tool execution time, in the first implementation or a later iteration.
3. Whether environment metadata should live inside `objective_metrics` or a broader solution `metadata` object.
