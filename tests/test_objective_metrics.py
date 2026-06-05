import unittest

from src.objective import compute_objective_metrics, is_submission_command


class ObjectiveMetricsTest(unittest.TestCase):
    def test_counts_action_and_excludes_submit(self):
        trajectory = {
            "info": {"model_stats": {"api_calls": 2}},
            "messages": [
                {
                    "role": "assistant",
                    "extra": {"actions": [{"command": "sed -i 's/a/b/' file.py"}]},
                },
                {
                    "role": "user",
                    "extra": {"returncode": 0},
                },
                {
                    "role": "assistant",
                    "extra": {
                        "actions": [
                            {"command": "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"}
                        ]
                    },
                },
                {"role": "exit"},
            ],
        }

        metrics = compute_objective_metrics(trajectory, 4.9499)

        self.assertEqual(metrics.completion_time_seconds, 4.95)
        self.assertEqual(metrics.step_count, 1)
        self.assertEqual(metrics.raw_action_count, 2)
        self.assertEqual(metrics.model_call_count, 2)

    def test_counts_multiple_solution_steps(self):
        trajectory = {
            "messages": [
                {"role": "assistant", "extra": {"actions": [{"command": "ls"}]}},
                {
                    "role": "assistant",
                    "extra": {"actions": [{"command": "pytest && ruff check ."}]},
                },
            ]
        }

        metrics = compute_objective_metrics(trajectory, 1.2)

        self.assertEqual(metrics.step_count, 2)
        self.assertEqual(metrics.raw_action_count, 2)
        self.assertIsNone(metrics.model_call_count)

    def test_handles_missing_messages_and_model_stats(self):
        metrics = compute_objective_metrics({}, 0.004)

        self.assertEqual(metrics.completion_time_seconds, 0.004)
        self.assertEqual(metrics.step_count, 0)
        self.assertEqual(metrics.raw_action_count, 0)
        self.assertIsNone(metrics.model_call_count)

    def test_submission_command_detection(self):
        self.assertTrue(
            is_submission_command("  echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n")
        )
        self.assertTrue(
            is_submission_command(
                'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT "Changed the parser"'
            )
        )
        self.assertFalse(
            is_submission_command("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && pwd")
        )


if __name__ == "__main__":
    unittest.main()
