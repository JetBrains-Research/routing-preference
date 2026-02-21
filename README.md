# Routing Preference

Optimal routing requires understanding which characteristics users desire the most for specific task types.

## Overview

This research project investigates how different characteristics of AI-generated code solutions affect user preferences and willingness to pay. By presenting users with pairs of solutions that vary in specific characteristics, we aim to estimate the value users place on each characteristic.

### Pipeline

1. **Issue Collection**: Gather open issues (first from JetBrains, then from GitHub)
2. **Issue Filtering**: Accepting/rejecting each issue for inclusion
3. **Solution Generation**: Generate a pool of solutions using different models
4. **Solution Sampling**: Select 2 solutions that differ in characteristics
5. **User Study**: Present PR-style solutions

### Characteristics Under Study

#### Quality Characteristics [Q]
- **Intent Understanding**: How well the solution addresses what the user actually wants
- **Correctness**: Whether the code works as expected
- **Scope Adherence**: Staying within the bounds of the requested changes
- **Code Quality**: Adherence to best practices, readability, maintainability

#### Performance Characteristics [P]
- **Response Speed**: How quickly the AI generates and displays suggestions
- **Task Completion Time**: Total time until the AI finishes its response
- **Resource Efficiency**: Computational resources consumed
- **Cost of Generation**: API/compute costs

### User Study Questions

1. **Preference**: Which solution (A or B) is better?
2. **Willingness to Pay**: Would you pay USD [5-30] more for the better one?
3. **Attribute Importance**: Which characteristics influenced your decision?
4. **Ranking**: Order characteristics by impact on your choice

Additional considerations:
- Subscription vs. price-per-PR framing
- Comparative/relative questioning approach
- Anchoring effects
- Demographic questions

### Models

| Model | Purpose |
|-------|---------|
| Qwen 8B | Baseline / lightweight |
| Qwen 32B | Mid-Tier |
| GLM-4.7 | SOTA (Z AI) |
| Qwen 235B | Mid-tier |
| Claude Opus 4.5 | SOTA (Anthropic) |
| OpenAI o5.2 | SOTA (OpenAI) |
| Kimi-k2 | SOTA(Moonshot) |

## Quick Start

```bash
git clone --recurse-submodules https://github.com/YOUR_ORG/routing-preference.git
cd routing-preference
make setup
```

See [GUIDE.md](GUIDE.md) for full instructions.

## Related Work

- [Analysing generative AI coding tools](https://lau.ucsd.edu/pubs/2025_analysis-of-90-genai-coding-tools_VLHCC.pdf)
- [SAGE: Systematic Analysis of GenAI Evaluation](https://journals-sagepub-com.tudelft.idm.oclc.org/doi/full/10.1177/20539517241290217)
- [Automated Code Generation Systems](https://www.mdpi.com/2079-8954/12/5/176)
- [arXiv:2511.07401](https://arxiv.org/abs/2511.07401)
- [arXiv:2511.09612](https://arxiv.org/abs/2511.09612)

## Project Structure

```
routing-preference/
├── src/
│   ├── collection/        # Issue collection from JetBrains/GitHub
|   ├── filter/            # Issue filtering
│   ├── generation/        # Solution generation with different models
│   └── sampling/          # Solution pair sampling logic
├── data/
│   ├── issues/            # Collected and validated issues
│   ├── solutions/         # Generated solutions
│   └── responses/         # User study responses
├── configs/               # Model and experiment configurations
├── scripts/               # Utility scripts
└── tests/                 # Test suite
```
