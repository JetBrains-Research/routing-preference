# Estimated Completion Time

The completion time displayed to survey participants is an estimate computed from each solution's own trajectory, not the measured wall-clock duration.
This document describes why, how it is computed, and how each number is justified.

## Why not the measured time

The measured wall-clock durations depend on conditions that have nothing to do with the solution being judged:

- OpenRouter routes each request to one of many providers, whose serving speed for the same model differs by an order of magnitude.
- Some batches ran concurrently on the same machine, inflating each other's times.
- Individual runs were inflated by incidents: commands hanging until the timeout, provider outages, and API credit interruptions mid-run.

Displaying these times would attribute serving luck to the models being compared.

## The estimate

```text
estimated_seconds = calls  x ttft_p50_seconds
                  + completion_tokens / speed_tps
                  + steps  x 0.56
```

- `calls` is the number of LLM requests in the run (assistant turns in the trajectory).
- `completion_tokens` is the total number of tokens the model generated, summed from the per-call `usage` reports stored in the trajectory (reasoning tokens included).
- `steps` is the number of executed commands (`step_count` in `info.json`).
- `ttft_p50_seconds` and `speed_tps` are per-model constants from `configs/models.yaml`: the p50 time-to-first-token and throughput of the model's pinned OpenRouter provider, from the OpenRouter endpoint statistics API (retrieved 2026-07-13).
- `0.56` seconds per command is the timeout-trimmed mean of 3,974 command durations measured directly from the trajectories (each command's duration is the gap between the assistant message timestamp and the following observation timestamp; commands that hit the 120s/600s execution timeout are excluded).

Every quantity is therefore either counted from the run itself or externally sourced and dated; nothing is fitted or hand-picked.

## Validation and sensitivity

- The estimates correlate with the measured wall-clock times at Spearman ρ = 0.73 over all 154 solutions; the residual is dominated by the serving noise listed above.
- The pairwise ordering of solutions is insensitive to the constants: doubling the time-to-first-token and multiplying the per-command constant by ~5 changes the ordering correlation by less than 0.04 (Spearman ≥ 0.97 vs the base estimate).

## Artifacts

- Computation: `scripts/estimate_completion_times.py` (run with `--sensitivity` to reproduce the numbers above).
- Output: `data/exports/estimated_completion_times.json`, one entry per solution.
- Display: the survey PR description ends with a `Completion time: ~N seconds` line taken from that file.
