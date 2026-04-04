# Agent

## Overview

The agent uses mini-swe-agent to generate solutions for GitHub issues. It clones the repository, runs the agent with a prompt, and captures the resulting diff.

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
