# Routing Preference

Research project studying what characteristics users value in AI-generated code solutions and how much they're willing to pay for them.

## Setup

```bash
git clone --recurse-submodules https://github.com/JetBrains-Research/routing-preference.git
cd routing-preference
make setup
cp .env.example .env  # add your API keys
```

## Usage

```bash
uv run generate --dataset "dataset-name" --model "openai/gpt-4o"
```

## Docs

- [GUIDE.md](GUIDE.md) - Setup and usage details
- [docs/PROJECT.md](docs/PROJECT.md) - Research overview
- [docs/PLAN.md](docs/PLAN.md) - Implementation plan
