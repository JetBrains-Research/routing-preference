# Objective Characteristics

Objective characteristics are measured from the solution-generation run. They do not use LLM judge prompts.

The project currently uses two objective characteristics:

| Characteristic | Metric ID | Description |
|----------------|-----------|-------------|
| **Completion Time** | `completion_time` | Total wall-clock time for the agent to create the solution. |
| **Step Count** | `step_count` | Number of solution-work agent steps taken before submission. |

Together with the four subjective LLM-judged characteristics, these make up the six characteristics used for comparing solutions.

## Measurement Scope

Objective measurements should be captured during solution generation and stored with the solution. They should be computed by code from timestamps and trajectory data, not by an LLM.

The generation environment affects these metrics. To keep comparisons fair, all seven model solutions for an issue should be generated under the same controlled execution setup.

Recommended controls:
- Use the same machine or runner for all compared models.
- Use the same sandbox mode and Docker image where possible.
- Avoid concurrent generation runs when measuring timing-sensitive fields.
- Store environment metadata with each solution.
- Keep setup time separate from solution-creation time.

## Characteristics

- [Completion Time](objective/COMPLETION_TIME.md)
- [Step Count](objective/STEP_COUNT.md)

## Related Non-Characteristic Measurements

Model response latency can be useful diagnostic data, but it is not currently one of the six characteristics. In this agent setup, the final patch is produced through filesystem changes and `git diff`, not as a single streamed final answer, so "response time" is ambiguous unless defined as a separate provider/model latency metric.
