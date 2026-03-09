# Getting Started

## Prerequisites

- Python 3.10+
- [Bun](https://bun.sh/) runtime
- [GitHub CLI](https://cli.github.com/) (`gh`)

## Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/YOUR_ORG/routing-preference.git
cd routing-preference

# Install dependencies
make setup
```

## Configure

### 1. API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys depend on which models you want to use:
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude models

### 2. OpenCode Configuration

```bash
mkdir -p ~/.config/opencode
cp configs/opencode.json ~/.config/opencode/opencode.json
```

Edit `~/.config/opencode/opencode.json` and replace `${LITELLM_MASTER_KEY}` with your actual key (same as in `.env`).

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

# Using the Python script directly
python scripts/generate.py --repo owner/repo --issue 123 --model gpt-4o-mini
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
