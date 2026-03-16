# Getting Started

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- [GitHub CLI](https://cli.github.com/) (`gh`) - For cloning repositories

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
git clone --recurse-submodules https://github.com/JetBrains-Research/routing-preference.git
cd routing-preference

# Install everything
make setup
```

This creates a `.venv` and installs all dependencies including mini-swe-agent.

## Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys depend on which models you want to use:
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude models

## Running

Generate solutions from the HuggingFace dataset:

```bash
# Basic usage
uv run generate --dataset "not/created/yet" --model openai/gpt-4o-mini

# Limit number of issues
uv run generate --dataset "not/created/yet" --model openai/gpt-4o-mini --limit 5

# Using make
make generate DATASET=not/created/yet MODEL=openai/gpt-4o-mini
```

## Available Models

Models are specified in LiteLLM format (`provider/model`):

| Provider | Models |
|----------|--------|
| OpenAI | `openai/gpt-4o-mini`, `openai/gpt-4o` |
| Anthropic | `anthropic/claude-sonnet-4-5-20250929`, `anthropic/claude-opus-4-5` |

## Output

Solutions are saved to `data/solutions/` as JSON files containing:
- Issue ID and details
- Model used
- Generated diff
- Full agent trajectory
- Timing and cost information

## Cleanup

```bash
# Remove generated data
make clean

# Remove everything including venv
make clean-all
```
