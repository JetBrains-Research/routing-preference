# Agent

## Overview

The agent uses mini-swe-agent to generate solutions for GitHub issues. It clones the repository, runs the agent with a prompt, captures the resulting diff, and stores run metadata in `info.json`.

## Prompt Templates

Prompts are loaded from `docs/agent/prompts/`:

```
docs/agent/
  prompts.json          # Configuration
  prompts/
    V1.md               # Default template for GitHub issues
    V1_zero_shot.md     # Template for zero-shot prompt tasks
```

Configuration in `prompts.json`. `defaults` maps a task type to its template;
`prompt` is the fallback when a task type has no entry:
```json
{
  "prompts": {
    "V1": "./prompts/V1.md",
    "V1_zero_shot": "./prompts/V1_zero_shot.md"
  },
  "defaults": {
    "prompt": "V1",
    "zero_shot": "V1_zero_shot"
  }
}
```

Templates use placeholders:
- `<ISSUE_TITLE>` - The issue title
- `<ISSUE_BODY>` - The issue description

The mini-swe-agent instance template asks the model to finish with:

```bash
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT "<summary>"
```

The text after the completion marker is stored as `summary` in the generated run's `info.json`.

## Usage

```bash
routing generate -d <dataset> -m <model>
routing generate -d <dataset> -m <model> --sandbox docker
```

## Execution Environments

| Environment | Description |
|-------------|-------------|
| `local` | Runs directly on host (default, faster for development) |
| `docker` | Runs in isolated container (safer for untrusted code) |
