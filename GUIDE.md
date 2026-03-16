# Getting Started

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- [GitHub CLI](https://cli.github.com/) (`gh`)

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
git clone https://github.com/YOUR_ORG/routing-preference.git
cd routing-preference

# Install everything
make setup
```

This creates a `.venv` and installs all dependencies.

## Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys depend on which models you want to use:
- `LITELLM_MASTER_KEY` - For LiteLLM proxy authentication
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude models

## Running

### Terminal 1: Start LiteLLM Proxy

```bash
make proxy
```

### Terminal 2: Generate Solutions

```bash
# Basic usage
make generate REPO=owner/repo ISSUE=123

# With specific model
make generate REPO=owner/repo ISSUE=123 MODEL=gpt-4o

# Using uv run directly
uv run python scripts/generate.py --repo owner/repo --issue 123 --model gpt-4o-mini
```

## Available Models

| Model | Provider | Notes |
|-------|----------|-------|
| gpt-4o-mini | openai | Fast, cheap |
| gpt-4o | openai | More capable |
| claude-sonnet-4.5 | anthropic | Balanced |
| claude-opus-4.5 | anthropic | Most capable |
| gemini-2.5-flash | gemini | Fast |
| gemini-2.5-pro | gemini | More capable |
| deepseek-v3.1 | deepseek | Good value |
| llama-3.3-70b | groq | Open source |

## Output

Solutions are saved to `data/solutions/` as JSON files containing:
- Issue details
- Model used
- Generated diff
- Full output log
- Timing information

## Cleanup

```bash
# Remove generated data
make clean

# Remove everything including venv
make clean-all
```
