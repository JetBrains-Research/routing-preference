# Judge Calibration Issue Set

This document defines how we collect the small issue set used to compare judge prompt variants.

The calibration set is separate from the final survey dataset. Its job is to expose differences between judge versions, not to represent the final participant-facing distribution.

## Target

Collect a locked set of about 15 GitHub issues. Each issue will be solved by all seven generation models, then judged by all judge variants. Manual scores will be used as the reference for comparing judge behavior.

## Issue Mix

Use a deliberately varied set:

- 3 simple documentation, typo, warning, or typing issues
- 4 small bug fixes with clear expected behavior
- 4 medium bug fixes that require reading nearby source code
- 2 small feature or enhancement requests
- 2 ambiguous or scope-sensitive issues where over-solving is plausible

Avoid issues that are mostly discussion, require broad redesign, depend on private services, need unusual external infrastructure, or are too large to manually score across seven generated solutions.

## Collection Process

1. Build a broad candidate pool from GitHub using the existing collector.
2. Keep candidates with usable issue descriptions, English text, non-bot authors, and no duplicate/invalid labels.
3. Fetch `base_commit` for each candidate so mini-swe-agent can solve against the repository state near issue creation.
4. Manually screen candidates down to the final 15.
5. Save the locked calibration set and do not reshuffle it while comparing judge variants.

Recommended candidate collection command:

```bash
uv run collect-issues collect \
  --repos pallets/flask pytest-dev/pytest Textualize/rich encode/httpx tiangolo/typer \
  --state all \
  --days 730 \
  --max-per-repo 80 \
  --fetch-commits \
  --batch-file judge_calibration_candidates.json
```

The final locked file is:

```text
data/issues/judge_calibration_15.json
```

This file is the input for solution generation:

```bash
uv run routing generate --dataset data/issues/judge_calibration_15.json --model <provider/model>
```

## Screening Criteria

Prefer issues where:

- The issue body states the desired behavior or failure mode clearly enough for manual scoring.
- A reasonable patch is expected to touch a small number of files.
- The issue can plausibly separate intent understanding, functional correctness, scope adherence, and code quality.
- The repository is public and installable enough for mini-swe-agent to explore.
- `base_commit` exists.

Reject issues where:

- The issue is only a question, support request, or duplicate.
- The expected answer depends mostly on maintainer preference.
- The fix requires credentials, hosted services, or non-public data.
- The likely solution is a large architectural change.
- The description is too vague to manually score generated solutions fairly.

## Manual Scoring

Manual scoring should use the same four subjective characteristics as the judge:

- Intent understanding
- Functional correctness
- Scope adherence
- Code quality

Objective characteristics are not judge-calibration targets because they are computed by code.

## Current Locked Set

The initial locked set was collected on 2026-05-07 from 201 filtered candidates.

| Bucket | Issue | Repository | Title |
| --- | --- | --- | --- |
| Simple docs/typing | `pallets__flask-5988` | `pallets/flask` | Docs: doubled word "the the" in TESTING config description |
| Simple docs/typing | `Textualize__rich-4050` | `Textualize/rich` | [Typo] Standardize library name to "Rich" in README.ja.md |
| Simple docs/typing | `Textualize__rich-3834` | `Textualize/rich` | [BUG] Docstring mismatch: reset(..., visible=None) says "Defaults to True" |
| Small bug | `Textualize__rich-4109` | `Textualize/rich` | [BUG] Hyperlinks are split into multiple links when text is highlighted |
| Small bug | `Textualize__rich-4090` | `Textualize/rich` | [BUG] Text.from_ansi leaves empty lines when input string has CRLF line endings |
| Small bug | `Textualize__rich-4041` | `Textualize/rich` | `FileProxy.isatty()` always returns `False` instead of delegating to the proxied file |
| Small bug | `tiangolo__typer-1159` | `tiangolo/typer` | [BUG] help line length miscalculated when using stylized text |
| Medium bug | `pallets__flask-5965` | `pallets/flask` | fix: celery task result endpoint crashes on task failure |
| Medium bug | `pytest-dev__pytest-14263` | `pytest-dev/pytest` | Session-end `gc.collect()` in `unraisableexception` plugin runs after warning filters are torn down, silently losing `ResourceWarning`s |
| Medium bug | `Textualize__rich-3927` | `Textualize/rich` | [BUG] traceback ignoring locals that are functions or classes |
| Medium bug | `pytest-dev__pytest-14389` | `pytest-dev/pytest` | Exception should be direct cause of `AssertionError` from `raises` context manager on failure for exception to match pattern rather than context |
| Feature | `tiangolo__typer-1242` | `tiangolo/typer` | Add support for command and subcommand aliases |
| Feature | `Textualize__rich-4034` | `Textualize/rich` | [REQUEST] SpeedColumn for arbitrary units (rows, files, it/s) |
| Scope-sensitive | `pallets__flask-5916` | `pallets/flask` | `provide_automatic_options` is weird |
| Scope-sensitive | `pallets__flask-5718` | `pallets/flask` | Recommend Warning and Safer Defaults for url_for(..., _external=True) |
