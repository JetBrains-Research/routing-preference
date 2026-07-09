"""Solution generation."""

import json
import logging
import os
import re
import shutil
import stat
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

from minisweagent.agents import get_agent
from minisweagent.config import get_config_from_spec
from minisweagent.environments import get_environment
from minisweagent.models import get_model
from minisweagent.utils.serialize import recursive_merge

from .models import Issue, Solution, SolutionInfo
from .objective import compute_objective_metrics
from .templating import fill_template

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 600
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
AGENT_DIR = PROJECT_ROOT / "docs" / "agent"
MODELS_CONFIG_PATH = PROJECT_ROOT / "configs" / "models.yaml"
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


def load_provider_order(
    model_name: str, config_path: Path = MODELS_CONFIG_PATH
) -> list[str] | None:
    """Return the configured OpenRouter provider order for a model, if any."""
    if not config_path.exists():
        return None
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    for entry in (config.get("models") or {}).values():
        openrouter = (entry.get("providers") or {}).get("openrouter") or {}
        if openrouter.get("model") == model_name:
            order = openrouter.get("provider_order")
            return [str(p) for p in order] if order else None
    return None


class SolutionGenerator:
    def __init__(
        self, environment_type: str = "local", prompt_version: str | None = None
    ):
        """Initialize the solution generator.

        Args:
            environment_type: "local" or "docker".
            prompt_version: template version.
        """
        if environment_type not in ("local", "docker"):
            raise ValueError(f"Unknown environment type: {environment_type}")
        if environment_type == "docker":
            self._check_docker_available()
        self.environment_type = environment_type
        self.prompt_version = prompt_version
        self._prompt_templates: dict[str, str] = {}

    def _check_docker_available(self) -> None:
        """Check if Docker is available and running."""
        try:
            subprocess.run(
                ["docker", "version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except Exception:
            raise RuntimeError("Docker is not running!")

    def _remove_workspace(self, workspace: Path) -> None:
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
    ) -> tuple[Solution, SolutionInfo]:
        """Generate a solution

        Args:
            issue: Issue
            model: name in LiteLLM format
            timeout: in seconds
        """
        workspace_base = PROJECT_ROOT / "data" / "workspaces"
        workspace_base.mkdir(parents=True, exist_ok=True)

        workspace_name = self._make_workspace_name(issue)
        workspace = workspace_base / workspace_name

        if workspace.exists():
            self._remove_workspace(workspace)

        # Extract top-level provider/gateway
        provider = model.split("/")[0] if "/" in model else "unknown"

        try:
            self._prepare_workspace(issue, workspace, timeout=timeout)
            prompt = self._build_prompt(issue)

            start = time.monotonic()
            trajectory, diff, exposed_files, grep_exposed_files = self._run_agent(
                workspace, model, prompt, timeout
            )
            completion_time_seconds = time.monotonic() - start
            duration_ms = int(completion_time_seconds * 1000)
            objective_metrics = compute_objective_metrics(
                trajectory,
                completion_time_seconds,
            )
            summary = trajectory.get("info", {}).get("submission", "").strip()

            solution = Solution(
                issue_id=issue.issue_id,
                model=model,
                provider=provider,
                diff=diff,
                trajectory=trajectory,
                duration_ms=duration_ms,
                created_at=datetime.now().isoformat(),
            )
            info = SolutionInfo(
                summary=summary,
                objective_metrics=objective_metrics,
                exposed_files=exposed_files,
                grep_exposed_files=grep_exposed_files,
            )
            return solution, info
        finally:
            if workspace.exists():
                self._remove_workspace(workspace)

    def _prepare_workspace(
        self,
        issue: Issue,
        workspace: Path,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Clone the task's repo, or init an empty repo for zero-shot tasks."""
        if issue.repo:
            self._clone_repo(
                issue.repo,
                workspace,
                timeout=timeout,
                base_commit=issue.base_commit,
            )
            if issue.base_commit:
                self._checkout_commit(workspace, issue.base_commit, timeout=timeout)
        else:
            self._init_workspace(
                workspace, timeout=timeout, seed_dir=issue.assets_dir
            )

    def _init_workspace(
        self,
        workspace: Path,
        timeout: int = DEFAULT_TIMEOUT,
        seed_dir: str | None = None,
    ) -> None:
        """Create a git workspace, seeded with provided asset files if any.

        Seeded files are part of the initial commit so they never appear in
        the solution diff.
        """
        workspace.mkdir(parents=True, exist_ok=True)
        if seed_dir:
            source = Path(seed_dir)
            if not source.is_dir():
                raise RuntimeError(f"Workspace seed directory not found: {source}")
            shutil.copytree(source, workspace / source.name)
        identity = ["-c", "user.name=routing", "-c", "user.email=routing@localhost"]
        for cmd in (
            ["git", "init"],
            ["git", "add", "-A"],
            ["git", *identity, "commit", "--allow-empty", "-m", "Initial commit"],
        ):
            try:
                subprocess.run(
                    cmd,
                    cwd=workspace,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"workspace init failed ({' '.join(cmd)}).\n"
                    f"stderr: {e.stderr or ''}"
                ) from e

    def _clone_repo(
        self,
        repo: str,
        dest: Path,
        timeout: int = DEFAULT_TIMEOUT,
        base_commit: str | None = None,
    ) -> None:
        # Use shallow clone only if no specific commit needed
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
                f"git checkout failed for {commit}.\nstderr: {e.stderr or ''}"
            ) from e

    def _make_workspace_name(self, issue: Issue) -> str:
        base = issue.repo or issue.issue_id or "task"
        safe_base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
        safe_base = safe_base.strip("._-") or "task"
        if len(safe_base) > 100:
            safe_base = safe_base[:100]
        suffix = uuid.uuid4().hex[:8]
        if issue.number:
            return f"{safe_base}_{issue.number}_{suffix}"
        return f"{safe_base}_{suffix}"

    def _load_prompt_template(self, task_type: str) -> str:
        cached = self._prompt_templates.get(task_type)
        if cached is not None:
            return cached

        config = json.loads((AGENT_DIR / "prompts.json").read_text(encoding="utf-8"))
        defaults = config["defaults"]
        version = self.prompt_version or defaults.get(task_type) or defaults["prompt"]
        prompt_path = AGENT_DIR / config["prompts"][version].lstrip("./")
        template = prompt_path.read_text(encoding="utf-8")
        self._prompt_templates[task_type] = template
        return template

    def _build_prompt(self, issue: Issue) -> str:
        template = self._load_prompt_template(issue.task_type or "github_issue")
        return fill_template(
            template,
            {"<ISSUE_TITLE>": issue.title, "<ISSUE_BODY>": issue.body},
        )

    def _run_agent(
        self,
        workspace: Path,
        model_name: str,
        prompt: str,
        timeout: int,
    ) -> tuple[dict, str, list[str], list[str]]:
        """Run mini-swe-agent and return trajectory, diff, and exposure lists."""
        base_config = get_config_from_spec("default")

        if self.environment_type == "docker":
            docker_image = os.getenv("ROUTING_SANDBOX_IMAGE", DEFAULT_DOCKER_IMAGE)
            env_config = {
                "environment_class": "docker",
                "image": docker_image,
                "cwd": "/workspace",
                "timeout": timeout,
                "forward_env": [
                    "GITHUB_TOKEN",
                    "GH_TOKEN",
                    "OPENAI_API_KEY",
                    "OPENROUTER_API_KEY",
                    "ANTHROPIC_API_KEY",
                    "GEMINI_API_KEY",
                    "DEEPSEEK_API_KEY",
                    "GROQ_API_KEY",
                ],
                "run_args": [
                    "--rm",
                    f"--user={os.getuid()}:{os.getgid()}",
                    "-v",
                    f"{workspace}:/workspace",
                ],
            }
        else:
            env_config = {
                "cwd": str(workspace),
                "timeout": timeout,
            }

        model_config = {
            "model_name": model_name,
            "cost_tracking": "ignore_errors",
            "model_class": "litellm_textbased",
        }
        provider_order = load_provider_order(model_name)
        if provider_order:
            model_config["model_kwargs"] = {
                "extra_body": {
                    "provider": {
                        "order": provider_order,
                        "allow_fallbacks": True,
                    }
                }
            }

        config = recursive_merge(
            base_config,
            {
                "model": model_config,
                "environment": env_config,
                "agent": {
                    "cost_limit": 10.0,
                },
            },
        )

        # Initialize components
        model = get_model(config=config.get("model", {}))
        env = get_environment(
            config.get("environment", {}), default_type=self.environment_type
        )
        agent = get_agent(model, env, config.get("agent", {}), default_type="default")

        agent.run(prompt)
        trajectory = agent.serialize()
        exposed_files = list(getattr(env, "exposed_files", []))
        grep_exposed_files = list(getattr(env, "grep_exposed_files", []))

        diff = self._capture_diff(workspace)
        return trajectory, diff, exposed_files, grep_exposed_files

    def _capture_diff(self, workspace: Path) -> str:
        """Capture the solution diff, including newly created files."""
        try:
            subprocess.run(
                ["git", "add", "-N", "."],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.warning(
                "git add -N failed; new files may be missing from the diff: %s",
                e.stderr,
            )

        try:
            diff_result = subprocess.run(
                ["git", "diff"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True,
            )
            return diff_result.stdout
        except subprocess.CalledProcessError as e:
            return f"git diff failed (rc={e.returncode}): {e.stderr}"
