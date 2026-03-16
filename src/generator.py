"""Solution generation using mini-swe-agent."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from minisweagent.agents import get_agent
from minisweagent.config import get_config_from_spec
from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.utils.serialize import recursive_merge

from .models import Issue, Solution

DEFAULT_TIMEOUT = 600  # 10 minutes
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class SolutionGenerator:
    """Generates solutions using mini-swe-agent."""

    def generate(
        self,
        issue: Issue,
        model: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Solution:
        """Generate a solution for an issue using a specific model.

        Args:
            issue: The issue to solve.
            model: Model name in LiteLLM format (e.g., "anthropic/claude-sonnet-4-5-20250929").
            timeout: Timeout in seconds.
        """
        workspace_base = PROJECT_ROOT / "data" / "workspaces"
        workspace_base.mkdir(parents=True, exist_ok=True)

        workspace_name = f"{issue.repo.replace('/', '_')}_{issue.number}"
        workspace = workspace_base / workspace_name

        if workspace.exists():
            shutil.rmtree(workspace)

        # Extract provider from model name (e.g., "anthropic/claude-..." -> "anthropic")
        provider = model.split("/")[0] if "/" in model else "unknown"

        try:
            self._clone_repo(issue.repo, workspace)
            prompt = self._build_prompt(issue)

            start = datetime.now()
            output, diff = self._run_agent(workspace, model, prompt, timeout)
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

            return Solution(
                issue_id=issue.id,
                model=model,
                provider=provider,
                diff=diff,
                output=output,
                duration_ms=duration_ms,
                created_at=datetime.now().isoformat(),
            )
        finally:
            if workspace.exists():
                shutil.rmtree(workspace)

    def _clone_repo(self, repo: str, dest: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Clone a repository to the destination path."""
        try:
            subprocess.run(
                ["gh", "repo", "clone", repo, str(dest), "--", "--depth", "1"],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"gh repo clone timed out after {timeout}s for {repo}.\n"
                f"stderr: {e.stderr or ''}"
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"gh repo clone failed for {repo} (rc={e.returncode}).\n"
                f"stderr: {e.stderr or ''}"
            ) from e

    def _build_prompt(self, issue: Issue) -> str:
        """Build the prompt for the agent."""
        return f"""Solve this GitHub issue:

Title: {issue.title}

Description:
{issue.body}

Implement the solution. Only modify the necessary files."""

    def _run_agent(
        self,
        workspace: Path,
        model_name: str,
        prompt: str,
        timeout: int,
    ) -> tuple[str, str]:
        """Run mini-swe-agent and return (trajectory_json, diff).

        Args:
            workspace: Path to the cloned repository.
            model_name: Model name in LiteLLM format.
            prompt: The task prompt.
            timeout: Timeout in seconds for each command.

        Returns:
            Tuple of (trajectory as JSON string, git diff).
        """
        # Load default config and merge with our settings
        base_config = get_config_from_spec("default")
        config = recursive_merge(
            base_config,
            {
                "model": {
                    "model_name": model_name,
                    "cost_tracking": "ignore_errors",
                },
                "environment": {
                    "cwd": str(workspace),
                    "timeout": timeout,
                },
                "agent": {
                    "cost_limit": 10.0,  # $10 limit per issue
                },
            },
        )

        # Initialize components
        model = get_model(config=config.get("model", {}))
        env = get_environment(config.get("environment", {}), default_type="local")
        agent = get_agent(model, env, config.get("agent", {}), default_type="default")

        # Run the agent
        agent.run(prompt)

        # Serialize the trajectory
        trajectory = json.dumps(agent.serialize(), indent=2)

        # Get git diff
        try:
            diff_result = subprocess.run(
                ["git", "diff"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True,
            )
            diff = diff_result.stdout
        except subprocess.CalledProcessError as e:
            diff = f"git diff failed (rc={e.returncode}): {e.stderr}"

        return trajectory, diff
