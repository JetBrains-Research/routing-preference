"""Solution generation using mini-swe-agent."""

import logging
import os
import re
import shutil
import stat
import subprocess
from datetime import datetime
from pathlib import Path
import uuid

from minisweagent.agents import get_agent
from minisweagent.config import get_config_from_spec
from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.utils.serialize import recursive_merge

from .models import Issue, Solution

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 600  # 10 minutes
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class SolutionGenerator:
    """Generates solutions using mini-swe-agent."""

    def _remove_workspace(self, workspace: Path) -> None:
        """Safely remove a workspace directory without masking underlying errors."""
        if not workspace.exists():
            return

        def _onerror(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                logger.warning(
                    "Failed to remove path %s during workspace cleanup",
                    path,
                    exc_info=True,
                )

        try:
            shutil.rmtree(workspace, onerror=_onerror)
        except Exception:
            logger.warning(
                "Failed to remove workspace %s",
                workspace,
                exc_info=True,
            )

    def generate(
        self,
        issue: Issue,
        model: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Solution:
        """Generate a solution for an issue using a specific model.

        Args:
            issue: The issue to solve.
            model: Model name in LiteLLM format. May have multiple '/' segments
                (e.g., "anthropic/claude-sonnet-4-5-20250929" or
                "openrouter/anthropic/claude-3-5-sonnet"). The first segment
                is recorded as ``provider`` in the resulting Solution.
            timeout: Timeout in seconds.
        """
        workspace_base = PROJECT_ROOT / "data" / "workspaces"
        workspace_base.mkdir(parents=True, exist_ok=True)

        workspace_name = self._make_workspace_name(issue)
        workspace = workspace_base / workspace_name

        if workspace.exists():
            self._remove_workspace(workspace)

        # Extract top-level provider/gateway (first segment of LiteLLM model ID)
        provider = model.split("/")[0] if "/" in model else "unknown"

        try:
            self._clone_repo(
                issue.repo,
                workspace,
                timeout=timeout,
                base_commit=issue.base_commit,
            )
            if issue.base_commit:
                self._checkout_commit(workspace, issue.base_commit, timeout=timeout)
            prompt = self._build_prompt(issue)

            start = datetime.now()
            trajectory, diff = self._run_agent(workspace, model, prompt, timeout)
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)

            return Solution(
                issue_id=issue.id,
                model=model,
                provider=provider,
                diff=diff,
                trajectory=trajectory,
                duration_ms=duration_ms,
                created_at=datetime.now().isoformat(),
            )
        finally:
            if workspace.exists():
                self._remove_workspace(workspace)

    def _clone_repo(
        self,
        repo: str,
        dest: Path,
        timeout: int = DEFAULT_TIMEOUT,
        base_commit: str | None = None,
    ) -> None:
        """Clone a repository to the destination path."""
        # Use shallow clone only if no specific commit needed
        # GitHub doesn't allow fetching arbitrary commits by SHA in shallow clones
        cmd = ["gh", "repo", "clone", repo, str(dest)]
        if not base_commit:
            cmd.extend(["--", "--depth", "1"])
        try:
            subprocess.run(
                cmd,
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

    def _checkout_commit(
        self,
        workspace: Path,
        commit: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Checkout a specific commit in the workspace."""
        try:
            subprocess.run(
                ["git", "checkout", "--detach", commit],
                cwd=workspace,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"git checkout timed out after {timeout}s for {commit}.\n"
                f"stderr: {e.stderr or ''}"
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"git checkout failed for {commit}.\n"
                f"stderr: {e.stderr or ''}"
            ) from e

    def _make_workspace_name(self, issue: Issue) -> str:
        """Generate a safe, per-run workspace directory name for an issue."""
        safe_repo = re.sub(r"[^A-Za-z0-9._-]", "_", issue.repo or "repo")
        safe_repo = safe_repo.strip("._-") or "repo"
        if len(safe_repo) > 100:
            safe_repo = safe_repo[:100]
        suffix = uuid.uuid4().hex[:8]
        return f"{safe_repo}_{issue.number}_{suffix}"

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
    ) -> tuple[dict, str]:
        """Run mini-swe-agent and return (trajectory, diff).

        Args:
            workspace: Path to the cloned repository.
            model_name: Model name in LiteLLM format.
            prompt: The task prompt.
            timeout: Timeout in seconds for each command.

        Returns:
            Tuple of (trajectory dict, git diff).
        """
        # Load default config and merge with our settings
        base_config = get_config_from_spec("default")
        config = recursive_merge(
            base_config,
            {
                "model": {
                    "model_name": model_name,
                    "cost_tracking": "ignore_errors",
                    "model_class": "litellm_textbased",
                },
                "environment": {
                    "cwd": str(workspace),
                    "timeout": timeout,
                },
                "agent": {
                    "cost_limit": 10.0,
                },
            },
        )

        # Initialize components
        model = get_model(config=config.get("model", {}))
        env = get_environment(config.get("environment", {}), default_type="local")
        agent = get_agent(model, env, config.get("agent", {}), default_type="default")

        # Run the agent
        agent.run(prompt)

        # Get the trajectory as dict
        trajectory = agent.serialize()

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
