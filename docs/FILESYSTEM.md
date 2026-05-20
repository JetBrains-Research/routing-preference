# Filesystem Layout

This document describes the project-owned data layout under `data/`.

## Solutions

Generated solutions are stored issue-first, then model-first, then run-first:

```text
data/solutions/
  <issue_id>/
    <solution_model_slug>/
      <run_id>/
        issue.json
        solution.json
        info.json
        patch.diff
```

The issue and model folders are reused when they already exist. Each generation creates a new `run_id` folder so repeated runs are preserved.

`info.json` stores run metadata that is not part of the core solution payload:

```json
{
  "summary": "Short model-written summary of the solution.",
  "objective_metrics": {
    "completion_time_seconds": 4.95,
    "step_count": 1,
    "raw_action_count": 2,
    "model_call_count": 2
  },
  "exposed_files": ["src/app.py"],
  "grep_exposed_files": ["tests/test_app.py"]
}
```

Historical calibration runs that used the older sidecar-file layout are archived under:

```text
data/solutions_for_judge_calibration/
```

Example:

```text
data/solutions/Textualize__rich-4050/openai_gpt-4o-mini/20260507_131500_123456/
```

The solution id used by judgments and selection is:

```text
<solution_model_slug>__<run_id>
```

## Judgments

LLM judge outputs are stored issue-first because the issue is shared by all seven solutions, scoring judgments, ranking judgments, manual scores, and comparisons.

```text
data/judgments/
  <issue_id>/
    scoring/
      <judge_model_slug>__<exposure>_<all|characteristic>/
        <solution_id>.json
    ranking/
      <group_id>/
        <judge_model_slug>__<exposure>_<all|characteristic>.json
```

Examples:

```text
data/judgments/Textualize__rich-4050/scoring/openai_gpt-4o__V1_all/openai_gpt-4o-mini__20260507_131500_123456.json
data/judgments/Textualize__rich-4050/ranking/Textualize__rich-4050/openai_gpt-4o__V1_all.json
```

## Selections

Answer-pair selection outputs are stored per issue and selection source:

```text
data/selections/
  <issue_id>/
    <selection_source>__<judge_model_slug>__<exposure>_<all|characteristic>.json
    candidates/
      <selection_source>__<judge_model_slug>__<exposure>_<all|characteristic>.json
```

Selection can be based on different scoring or ranking judge runs. The current
implementation selects from scoring outputs, but the storage layout leaves room
for ranking-based selection outputs too.

Each selected solution is stored as a structured reference containing the
`solution_id`, `model_slug`, `run_id`, and path relative to `data/solutions/`.

The per-issue `candidates/` file stores all candidate pairs and their local
metrics for the same selection source.

Selection parameters are stored in:

```text
configs/selection.json
```

Global balanced selection also writes a run-level directory:

```text
data/selections/
  runs/
    <selection_run_id>/
      config.json
      summary.json
      candidates/
        <issue_id>.json
      selected/
        <issue_id>.json
```

Per-issue `candidates/` files contain all candidate pairs and their local
metrics. Run-level `candidates/<issue_id>.json` contains the scored candidate
pool used by the global selector. `summary.json` contains selected pairs across
issues, model usage, quality-band usage, and the selection method.

## Issues

Collected issue files live under:

```text
data/issues/
```

The locked judge calibration issue set is:

```text
data/issues/judge_calibration_15.json
```

## Workspaces

Temporary mini-swe-agent workspaces live under:

```text
data/workspaces/
```

They are execution scratch space, not primary research outputs.

## Reviewers

`data/reviewers/` belonged to an earlier maintainer-review workflow. It tracked imported repository maintainers, consent, and issue assignments.

The current calibration workflow uses manual scoring by the project owner instead, so reviewer storage is not part of the active pipeline.
