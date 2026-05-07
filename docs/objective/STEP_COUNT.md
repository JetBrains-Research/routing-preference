# Step Count

## Definition

Step count measures how many solution-work steps the agent took to create the solution.

Metric ID: `step_count`

Unit: count

## Measurement Boundary

Count mini-swe-agent assistant turns that attempted an executable agent action.

In the current text-based mini-swe-agent configuration, the model is required to emit exactly one `mswea_bash_command` block per normal action turn. Therefore a normal action turn corresponds to one executed bash command.

Exclude the final submission command:

```bash
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
```

The submission command is protocol overhead, not solution work.

## Edge Cases

Format-error turns should not count as solution-work steps because no environment action was executed.

Exit messages should not count as solution-work steps.

A single bash command may contain multiple shell operations joined with `&&`, `||`, `;`, or a script invocation. It still counts as one agent step because it came from one model decision turn.

## Current Status

Step count is stored in `solution.json` under `objective_metrics.step_count`.

The raw count of all assistant action turns, including the final submission command, is stored under `objective_metrics.raw_action_count` for diagnostics.
