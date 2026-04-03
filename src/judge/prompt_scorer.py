"""Single characteristic scoring using prompt templates."""

import json

import litellm

from ..models import Issue, Solution
from .loader import CharacteristicLoader, PromptLoader
from .models import Score


class PromptScorer:
    """Scores a single characteristic using prompt templates."""

    def __init__(
        self,
        model: str = "openai/gpt-4o",
        prompt_version: str = "V2.1",
    ):
        self.model = model
        self.prompt_version = prompt_version
        self.char_loader = CharacteristicLoader()
        self.prompt_loader = PromptLoader(characteristic_loader=self.char_loader)

    def score(
        self,
        characteristic_id: str,
        issue: Issue,
        solution: Solution,
    ) -> Score:
        """Score a solution on a single characteristic."""
        prompt = self._build_prompt(characteristic_id, issue, solution)
        response = self._call_llm(prompt)
        return self._parse_response(response, characteristic_id)

    def _build_prompt(
        self,
        characteristic_id: str,
        issue: Issue,
        solution: Solution,
    ) -> str:
        """Build the full prompt with issue and solution context."""
        template = self.prompt_loader.load_single_prompt(
            characteristic_id,
            version=self.prompt_version,
        )

        context = f"""
## Issue

**Title:** {issue.title}

**Description:**
{issue.body}

## Solution (patch.diff)

```diff
{solution.diff}
```
"""
        return template + "\n\n" + context

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM via LiteLLM."""
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty response")
        return content

    def _parse_response(self, response: str, characteristic_id: str) -> Score:
        """Parse JSON response into a Score."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {response[:200]}") from e

        score_value = data.get("score")
        reasoning = data.get("reasoning", "")

        if not isinstance(score_value, int) or not 1 <= score_value <= 5:
            raise ValueError(f"Score must be integer 1-5, got: {score_value}")

        return Score(
            characteristic_id=characteristic_id,
            value=score_value,
            reasoning=reasoning,
        )
