# Routing Preference

Research project studying what characteristics users value in AI-generated code solutions and how much they're willing to pay for them.

## Setup

```bash
git clone --recurse-submodules https://github.com/JetBrains-Research/routing-preference.git
cd routing-preference
make setup   # also applies patches/track-exposed-files.patch to mini-swe-agent
cp .env.example .env  # add your API keys
```

The setup step applies `patches/track-exposed-files.patch` to the `mini-swe-agent` submodule so that file exposures (what the agent read during execution) are recorded alongside each generated solution. V2.1 judge scoring relies on this.

## Usage

```bash
uv run generate --dataset "dataset-name" --model "openai/gpt-4o"
```

## Docs

- [GUIDE.md](GUIDE.md) - Setup and usage details
- [docs/PROJECT.md](docs/PROJECT.md) - Research overview
- [docs/PLAN.md](docs/PLAN.md) - Implementation plan
- [docs/OBJECTIVE.md](docs/OBJECTIVE.md) - Objective characteristic definitions
