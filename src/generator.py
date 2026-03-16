"""Solution generation using mini-swe-agent."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

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

    def _clone_repo(self, repo: str, dest: Path) -> None:
        """Clone a repository to the destination path."""
        subprocess.run(
            ["gh", "repo", "clone", repo, str(dest), "--", "--depth", "1"],
            check=True,
            capture_output=True,
        )

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
        model: str,
        prompt: str,
        timeout: int,
    ) -> tuple[str, str]:
        """Run mini-swe-agent and return (output, diff)."""
        raise NotImplementedError("Agent integration not yet implemented")
