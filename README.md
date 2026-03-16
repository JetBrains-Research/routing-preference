# Routing Preference

Optimal routing requires understanding which characteristics users desire the most for specific task types.

## Overview

This research project investigates how different characteristics of AI-generated code solutions affect user preferences and willingness to pay. By presenting users with pairs of solutions that vary in specific characteristics, we aim to estimate the value users place on each characteristic.

### Pipeline

1. **Issue Dataset**: Load issues from the HuggingFace dataset
2. **Solution Generation**: Generate solutions using mini-swe-agent with different models
3. **Solution Sampling**: Select solution pairs that differ in characteristics
4. **User Study**: Present PR-style solutions for comparison

### Characteristics Under Study

#### Quality Characteristics
- **Intent Understanding**: How well the solution addresses what the user actually wants
- **Correctness**: Whether the code works as expected
- **Scope Adherence**: Staying within the bounds of the requested changes
- **Code Quality**: Adherence to best practices, readability, maintainability

#### Performance Characteristics
- **Response Speed**: How quickly the AI generates suggestions
- **Task Completion Time**: Total time until the AI finishes
- **Cost of Generation**: API/compute costs

## Quick Start

```bash
git clone --recurse-submodules https://github.com/YOUR_ORG/routing-preference.git
cd routing-preference
make setup
```

Configure API keys:
```bash
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
```

Generate solutions:
```bash
uv run generate --dataset "not/created/yet"
```

See [GUIDE.md](GUIDE.md) for full instructions.

## Project Structure

```
routing-preference/
├── src/
│   ├── cli.py           # CLI entry point
│   ├── dataset/         # HuggingFace dataset loader
│   ├── generator.py     # Solution generation with mini-swe-agent
│   ├── models.py        # Issue, Solution dataclasses
│   ├── pipeline.py      # Pipeline orchestrator
│   └── storage.py       # Solution storage (JSON)
├── data/
│   ├── solutions/       # Generated solutions
│   └── workspaces/      # Temporary cloned repos
├── configs/
│   └── models.yaml      # Model registry
├── external/
│   └── mini-swe-agent/  # Agent submodule
└── pyproject.toml
```

## Models

Models are specified in LiteLLM format (`provider/model`):

| Model | Example |
|-------|---------|
| OpenAI | `openai/gpt-4o`, `openai/gpt-4o-mini` |
| Anthropic | `anthropic/claude-sonnet-4-5`, `anthropic/claude-opus-4-5` |
