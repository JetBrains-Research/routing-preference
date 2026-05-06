"""Objective metrics computed from solution generation data."""

from dataclasses import dataclass

SUBMISSION_COMMAND = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"


@dataclass
class ObjectiveMetrics:
    """Objective measurements for a generated solution."""

    completion_time_seconds: float
    step_count: int
    raw_action_count: int
    model_call_count: int | None = None


def is_submission_command(command: str) -> bool:
    """Return True when the command is only the mini-swe-agent submit command."""
    return command.strip() == SUBMISSION_COMMAND


def compute_objective_metrics(
    trajectory: dict,
    completion_time_seconds: float,
) -> ObjectiveMetrics:
    """Compute objective metrics from a mini-swe-agent trajectory."""
    raw_action_count = 0
    step_count = 0

    for message in trajectory.get("messages", []):
        if message.get("role") != "assistant":
            continue

        actions = message.get("extra", {}).get("actions") or []
        if not actions:
            continue

        raw_action_count += 1

        commands = [
            action.get("command", "")
            for action in actions
            if isinstance(action, dict)
        ]
        if commands and all(is_submission_command(command) for command in commands):
            continue

        step_count += 1

    model_call_count = (
        trajectory.get("info", {}).get("model_stats", {}).get("api_calls")
    )
    if not isinstance(model_call_count, int):
        model_call_count = None

    return ObjectiveMetrics(
        completion_time_seconds=round(completion_time_seconds, 3),
        step_count=step_count,
        raw_action_count=raw_action_count,
        model_call_count=model_call_count,
    )
