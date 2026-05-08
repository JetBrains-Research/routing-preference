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
        objective_metrics.json
        patch.diff
        exposed_files.json
```

The issue and model folders are reused when they already exist. Each generation creates a new `run_id` folder so repeated runs are preserved.

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
      <judge_model_slug>__<exposure>_<all|characteristic>.json
```

Examples:

```text
data/judgments/Textualize__rich-4050/scoring/openai_gpt-4o__V1_all/openai_gpt-4o-mini__20260507_131500_123456.json
data/judgments/Textualize__rich-4050/ranking/openai_gpt-4o__V1_all.json
```

## Selections

Answer-pair selection outputs are stored per issue and selection source:

```text
data/selections/
  <issue_id>/
    <selection_source>__<judge_model_slug>__<exposure>_<all|characteristic>.json
```

Selection can be based on different scoring or ranking judge runs. The current
implementation selects from scoring outputs, but the storage layout leaves room
for ranking-based selection outputs too.

Each selected solution is stored as a structured reference containing the
`solution_id`, `model_slug`, `run_id`, and path relative to `data/solutions/`.

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
