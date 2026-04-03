"""Rank multiple solutions on a single characteristic."""

import re

import litellm

from ...models import Issue, Solution
from ..legacy import Characteristic
from .models import Ranking


class RankingScorer:
    """Ranks multiple solutions on a single characteristic."""

    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model

    def rank(
        self,
        characteristic: Characteristic,
        issue: Issue,
        solutions: list[Solution],
    ) -> Ranking:
        """Rank solutions on a single characteristic.

        Args:
            characteristic: The characteristic to rank on.
            issue: The original issue.
            solutions: List of solutions to compare.

        Returns:
            Ranking with model -> rank mapping.
        """
        prompt = self._build_prompt(characteristic, issue, solutions)
        response = self._call_llm(prompt)
        return self._parse_response(response, characteristic.id, solutions)

    def _build_prompt(
        self,
        characteristic: Characteristic,
        issue: Issue,
        solutions: list[Solution],
    ) -> str:
        """Build prompt presenting all solutions for comparison."""
        solutions_text = ""
        for i, sol in enumerate(solutions, 1):
            solutions_text += f"""
### Solution {i} (Model: {sol.model})
```diff
{sol.diff}
```
"""

        return f"""You are comparing multiple code solutions for a GitHub issue.

## Issue
**Title:** {issue.title}

**Description:**
{issue.body}

## Solutions
{solutions_text}

## Task
Rank ALL solutions on **{characteristic.name}**: {characteristic.description}

Consider: {self._get_criteria(characteristic.id)}

## Response Format
Rank from best (1) to worst ({len(solutions)}). Each solution must have a unique rank.

Respond with ONLY the following format:
Rankings:
Solution 1: <rank>
Solution 2: <rank>
...
Reasoning: <your explanation for the ranking>
"""

    def _get_criteria(self, characteristic_id: str) -> str:
        """Get evaluation criteria for a characteristic."""
        criteria = {
            "correctness": "Does the solution correctly solve the issue? Are there bugs?",
            "completeness": "Does it address all aspects? Are edge cases handled?",
            "readability": "Is the code easy to read? Are names clear?",
            "maintainability": "Is it well-structured? Easy to modify?",
            "efficiency": "Is it performant? No unnecessary operations?",
            "safety": "Does it handle errors? Avoid vulnerabilities?",
            "minimality": "Only necessary changes? No over-engineering?",
        }
        return criteria.get(characteristic_id, "")

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM via LiteLLM."""
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content

    def _parse_response(
        self,
        response: str,
        characteristic_id: str,
        solutions: list[Solution],
    ) -> Ranking:
        """Parse LLM response into a Ranking."""
        ranks: dict[str, int] = {}
        num_solutions = len(solutions)

        # Parse "Solution N: <rank>" patterns
        for i, sol in enumerate(solutions, 1):
            pattern = rf"Solution\s*{i}\s*:\s*(\d+)"
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                ranks[sol.model] = int(match.group(1))
            else:
                raise ValueError(
                    f"Could not parse rank for Solution {i} from response: {response[:200]}"
                )

        # Validate ranks are in valid range
        rank_values = list(ranks.values())
        if not all(1 <= r <= num_solutions for r in rank_values):
            raise ValueError(
                f"Ranks must be between 1 and {num_solutions}, got {rank_values}"
            )

        # Validate ranks are unique (no ties)
        if len(set(rank_values)) != num_solutions:
            raise ValueError(
                f"Ranks must be unique (1..{num_solutions}), got {rank_values}"
            )

        reasoning_match = re.search(
            r"Reasoning:\s*(.+)", response, re.IGNORECASE | re.DOTALL
        )
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        return Ranking(
            characteristic_id=characteristic_id,
            ranks=ranks,
            reasoning=reasoning,
        )
