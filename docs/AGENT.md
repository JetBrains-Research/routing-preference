# Agent

## Overview

The agent uses mini-swe-agent to generate solutions for GitHub issues. It clones the repository, runs the agent with a prompt, captures the resulting diff, and stores run metadata in `info.json`.

## Prompt Templates

Prompts are loaded from `docs/agent/prompts/`:

```
docs/agent/
  prompts.json          # Configuration
  prompts/
    V1.md               # Default prompt template
```

Configuration in `prompts.json`:
```json
{
  "prompts": { "V1": "./prompts/V1.md" },
  "defaults": { "prompt": "V1" }
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
