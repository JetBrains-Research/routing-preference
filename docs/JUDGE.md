# LLM as a Judge

## Overview

The judge evaluates solutions on 7 characteristics. These evaluations are used internally for **pair selection**, finding solution pairs with similar overall quality but different characteristic profiles. The scores are **not shown to users**.

Two modes are available:
- **Absolute Scoring**: Each solution scored 1-10 independently
- **Comparative Ranking**: All solutions for an issue ranked against each other

## Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Correctness** | Does the solution correctly solve the issue? |
| **Completeness** | Does it address all aspects of the issue? |
| **Readability** | Is the code easy to read and understand? |
| **Maintainability** | Is the code well-structured and maintainable? |
| **Efficiency** | Is the solution performant? |
| **Safety** | Does it handle edge cases and avoid vulnerabilities? |
| **Minimality** | Are only necessary changes made? |

## Usage

```bash
# Absolute scoring
python -m src.judge_cli                                    # Score all unjudged solutions
python -m src.judge_cli --solution <folder>                # Score a specific solution
python -m src.judge_cli --no-skip-existing                 # Re-score all solutions

# Comparative ranking
python -m src.judge_cli --rank sympy__sympy-11400          # Rank all solutions for an issue
```

## How It Works

### Absolute Scoring

1. **Input**: Issue (title + body) and one solution diff
2. **Process**: 7 LLM calls per solution (one per characteristic)
3. **Output**: Scores 1-10 with reasoning for each characteristic

### Comparative Ranking

1. **Input**: Issue and all solution diffs presented together
2. **Process**: 7 LLM calls per issue (one per characteristic)
3. **Output**: Rankings (1st, 2nd, 3rd...) for each characteristic

The judge sees only the diff, not the full agent trajectory.

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
    {"characteristic_id": "correctness", "value": 8, "reasoning": "..."},
    {"characteristic_id": "completeness", "value": 7, "reasoning": "..."}
  ],
  "overall_score": 7.86,
  "created_at": "2026-03-25T23:31:29"
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
| **Absolute Scoring** | Independent evaluation, when solutions arrive at different times |
| **Comparative Ranking** | Direct comparison, more reliable relative ordering |
