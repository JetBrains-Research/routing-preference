# LLM as a Judge

## Overview

The judge evaluates solutions on 4 characteristics using a 1-5 scale. Evaluations are used internally for **pair selection**, finding solution pairs with similar overall quality but different characteristic profiles. The scores are **not shown to users**.

Two scoring modes are available:
- **Batch** (default): All 4 characteristics scored in a single LLM call
- **Single**: One LLM call per characteristic (useful for debugging)

Additionally, **Comparative Ranking** can rank all solutions for an issue against each other.

## Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Intent** | How well the agent grasped what the issue was trying to accomplish or fix |
| **Correctness** | Whether the solution works correctly, regardless of what it targets |
| **Scope** | Whether the solution stays within the boundaries of what the issue requested |
| **Quality** | Readability, maintainability, documentation, and adherence to coding conventions |

Characteristic definitions and scoring rubrics are loaded from `docs/judge/characteristics/`.

## Usage

```bash
# Absolute scoring (batch mode - default)
judge                                      # Score all unjudged solutions
judge --solution <folder>                  # Score a specific solution
judge --no-skip-existing                   # Re-score all solutions

# Single mode (one call per characteristic)
judge --mode single

# Specify prompt version
judge --prompt-version V1                  # Batch prompt version
judge --mode single --prompt-version V2.1  # Single prompt version

# Comparative ranking
judge --rank sympy__sympy-11400            # Rank all solutions for an issue

# Other options
judge --judge-model anthropic/claude-sonnet-4  # Use a different judge model
judge -v                                   # Verbose logging
```

## How It Works

### Batch Scoring (Default)

1. **Input**: Issue (title + body) and solution diff
2. **Process**: Single LLM call scores all 4 characteristics
3. **Output**: JSON with scores 1-5 and reasoning for each characteristic

### Single Scoring

1. **Input**: Issue and solution diff
2. **Process**: 4 separate LLM calls (one per characteristic)
3. **Output**: Same format as batch

### Comparative Ranking

1. **Input**: Issue and all solution diffs presented together
2. **Process**: LLM ranks solutions against each other per characteristic
3. **Output**: Rankings (1st, 2nd, 3rd...) for each characteristic

The judge sees only the diff, not the full agent trajectory.

## Prompt Templates

Prompts are loaded from `docs/judge/prompts/`:

| File | Mode | Description |
|------|------|-------------|
| `JUDGE_SCORING_PROMPT_V*.md` | Single | Template for scoring one characteristic |
| `JUDGE_SCORING_ALL_PROMPT_V*.md` | Batch | Template for scoring all characteristics at once |

Templates use placeholders like `<CHARACTERISTIC_NAME.md>` that are replaced with content from the characteristic files.

## Output

### Absolute Scoring

Saved as `judgment.json` alongside each solution:

```
data/solutions/
  20260325_125319_sympy__sympy-11400_openai_gpt-4o-mini/
    issue.json
    solution.json
    patch.diff
    judgment.json
```

Example:

```json
{
  "solution_folder": "20260325_..._openai_gpt-4o-mini",
  "issue_id": "sympy__sympy-11400",
  "solution_model": "openai/gpt-4o-mini",
  "judge_model": "openai/gpt-4o",
  "scores": [
    {"characteristic_id": "intent", "value": 4, "reasoning": "..."},
    {"characteristic_id": "correctness", "value": 5, "reasoning": "..."},
    {"characteristic_id": "scope", "value": 4, "reasoning": "..."},
    {"characteristic_id": "quality", "value": 3, "reasoning": "..."}
  ],
  "overall_score": 4.0,
  "created_at": "2026-03-25T23:31:29",
  "prompt_version": "V1",
  "score_scale": [1, 5]
}
```

### Comparative Ranking

Saved per issue in `data/rankings/`:

```
data/rankings/
  sympy__sympy-11400.json
```

Example:

```json
{
  "issue_id": "sympy__sympy-11400",
  "solution_models": ["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-sonnet-4"],
  "judge_model": "openai/gpt-4o",
  "rankings": [
    {
      "characteristic_id": "correctness",
      "ranks": {"openai/gpt-4o": 1, "anthropic/claude-sonnet-4": 2, "openai/gpt-4o-mini": 3},
      "reasoning": "..."
    }
  ],
  "overall_ranks": {"openai/gpt-4o": 1.5, "anthropic/claude-sonnet-4": 2.0, "openai/gpt-4o-mini": 2.5},
  "created_at": "2026-03-25T23:45:00"
}
```

## When to Use Each Mode

| Mode | Best For |
|------|----------|
| **Batch** | Production use, faster and cheaper (1 LLM call vs 4) |
| **Single** | Debugging, testing individual characteristic prompts |
| **Ranking** | Direct comparison when you have multiple solutions for the same issue |
