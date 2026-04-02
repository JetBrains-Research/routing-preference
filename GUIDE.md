# Getting Started

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- [GitHub CLI](https://cli.github.com/) (`gh`) - For cloning repositories
- [Docker](https://www.docker.com/) (optional) - For sandboxed execution

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

## Running

Generate solutions from a dataset:

```bash
# Basic usage (local execution)
uv run generate --dataset data/issues/test.json --model openai/gpt-4o-mini

# Limit number of issues
uv run generate --dataset data/issues/test.json --model openai/gpt-4o-mini --limit 5

# Sandboxed execution (requires Docker)
uv run generate --dataset data/issues/test.json --model openai/gpt-4o-mini --sandbox docker

# Using make
make generate DATASET=data/issues/test.json MODEL=openai/gpt-4o-mini
```

### Sandbox Mode

By default, agents run locally on the host machine. For untrusted datasets, use `--sandbox docker` to run agents in an isolated container.

```bash
# Use custom Docker image (optional)
export ROUTING_SANDBOX_IMAGE=routing-sandbox:latest
uv run generate --dataset data/issues/untrusted.json --sandbox docker
```

See [docs/ISOLATION.md](docs/ISOLATION.md) for details.

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
