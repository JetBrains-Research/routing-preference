# Completion Time

## Definition

Completion time measures the total wall-clock time it took the agent to create a solution.

Metric ID: `completion_time`

Unit: seconds

## Measurement Boundary

Start measuring immediately before the mini-swe-agent run begins.

Stop measuring after the final solution diff has been captured.

This includes:
- LLM calls made by the agent
- Tool and shell command execution
- File reads and edits performed by the agent
- Tests or validation commands run by the agent
- The final `git diff` capture

This excludes:
- Loading the issue dataset
- Cloning the repository
- Checking out the base commit
- Saving the solution files to `data/solutions/`

## Fairness

Completion time is a system-level measurement. It includes both model latency and local execution time, so it can be affected by the runner machine, sandbox mode, Docker image, network conditions, and repository tooling.

For fair model comparison, all seven model solutions for the same issue should be generated under the same controlled environment.

Recommended implementation details:
- Use a monotonic clock.
- Store the measured value in seconds.
- Store component timings separately when possible, such as model wait time and tool execution time.
- Store environment metadata so timing data can be interpreted later.

## Current Status

Completion time is stored in `solution.json` under `objective_metrics.completion_time_seconds`.

The existing `duration_ms` field is kept for compatibility. It is derived from the same timing boundary.
