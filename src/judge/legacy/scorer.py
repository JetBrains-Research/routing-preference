"""Score a single characteristic"""

import re

import litellm

from ...models import Issue, Solution
from ..models import Characteristic, Score


class CharacteristicScorer:
    """Scores a single characteristic"""

    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model

    def score(
        self,
        characteristic: Characteristic,
        issue: Issue,
        solution: Solution,
    ) -> Score:
        """Score a solution on a single characteristic.

        Args:
            characteristic: The characteristic to score.
            issue: The original issue.
            solution: The generated solution.

        Returns:
            Score with value (1-10) and reasoning.
        """
        prompt = self._build_prompt(characteristic, issue, solution)
        response = self._call_llm(prompt)
        return self._parse_response(response, characteristic.id)

    def _build_prompt(
        self,
        characteristic: Characteristic,
        issue: Issue,
        solution: Solution,
    ) -> str:
        """Fill in the prompt template with solution details"""
        return characteristic.prompt_template.format(
            issue_title=issue.title,
            issue_body=issue.body,
            diff=solution.diff,
        )

    def _call_llm(self, prompt: str) -> str:
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content

    def _parse_response(self, response: str, characteristic_id: str) -> Score:
        """Parse LLM response into a Score.

        Expected format:
            Score: 7
            Reasoning: The solution correctly implements...
        """
        score_match = re.search(r"Score:\s*(\d+)", response, re.IGNORECASE)
        if not score_match:
            raise ValueError(f"Could not parse score from response: {response[:200]}")

        value = int(score_match.group(1))
        if not 1 <= value <= 10:
            raise ValueError(f"Score {value} is out of range 1-10")

        reasoning_match = re.search(r"Reasoning:\s*(.+)", response, re.IGNORECASE | re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        return Score(
            characteristic_id=characteristic_id,
            value=value,
            reasoning=reasoning,
        )
