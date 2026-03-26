# LLM as a Judge

## Overview

The judge scores each solution on 7 characteristics. These scores are used internally for **pair selection**, finding solution pairs with similar overall quality but different characteristic profiles. The scores are **not shown to users**.

## Characteristics

Each solution is scored 1-10 on these dimensions:

| Characteristic | Description |
|----------------|-------------|
| **Correctness** | Does the solution correctly solve the issue? |
| **Completeness** | Does it address all aspects of the issue? |
| **Readability** | Is the code easy to read and understand? |
| **Maintainability** | Is the code well-structured and maintainable? |
| **Efficiency** | Is the solution performant? |
| **Safety** | Does it handle edge cases and avoid vulnerabilities? |
| **Minimality** | Are only necessary changes made? |

## How It Works

1. **Input**: The judge receives the issue (title + body) and the solution diff
2. **Scoring**: For each characteristic, an LLM call evaluates the solution
3. **Output**: A judgment with 7 scores, reasoning for each, and an overall average

The judge does **not** see the full agent trajectory - only the final diff.

## Output

Judgments are saved as `judgment.json` alongside each solution:

```
data/solutions/
  20260325_125319_sympy__sympy-11400_openai_gpt-4o-mini/
    issue.json
    solution.json
    patch.diff
    judgment.json
```

Example `judgment.json`:

```json
{
  "solution_folder": "20260325_125319_sympy__sympy-11400_openai_gpt-4o-mini",
  "issue_id": "sympy__sympy-11400",
  "solution_model": "openai/gpt-4o-mini",
  "judge_model": "openai/gpt-4o",
  "scores": [
    {"characteristic_id": "correctness", "value": 8, "reasoning": "..."},
    {"characteristic_id": "completeness", "value": 7, "reasoning": "..."},
    ...
  ],
  "overall_score": 7.86,
  "created_at": "2026-03-25T23:31:29"
}
```

## Validation

Before full automation, a sub-sample of judgments should be manually reviewed to verify alignment between LLM scores and human assessment.
