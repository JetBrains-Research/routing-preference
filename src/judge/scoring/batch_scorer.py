"""Batch scoring of all characteristics in a single LLM call."""

import json

import litellm

from ...models import Issue, Solution
from ..loader import CharacteristicLoader, PromptLoader
from ..models import Score


class BatchScorer:
    """Scores all characteristics in a single LLM call."""

    # Canonical order for the 4 characteristics
    CHARACTERISTIC_ORDER = ["intent", "correctness", "scope", "quality"]

    def __init__(
        self,
        model: str = "openai/gpt-4o",
        prompt_version: str = "V1",
    ):
        self.model = model
        self.prompt_version = prompt_version
        self.char_loader = CharacteristicLoader()
        self.prompt_loader = PromptLoader(characteristic_loader=self.char_loader)

    def score_all(
        self,
        issue: Issue,
        solution: Solution,
    ) -> list[Score]:
        """Score a solution on all characteristics at once."""
        prompt = self._build_prompt(issue, solution)
        response = self._call_llm(prompt)
        return self._parse_response(response)

    def _build_prompt(self, issue: Issue, solution: Solution) -> str:
        """Build the full prompt with all characteristics."""
        template = self.prompt_loader.load_batch_prompt(
            characteristic_ids=self.CHARACTERISTIC_ORDER,
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

    def _parse_response(self, response: str) -> list[Score]:
        """Parse JSON response into list of Scores."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {response[:200]}") from e

        characteristics = data.get("characteristics", {})
        scores = []

        # Build name -> id mapping
        name_to_id = {}
        for cid in self.CHARACTERISTIC_ORDER:
            char = self.char_loader.load(cid)
            name_to_id[char.name] = cid

        for char_name, score_data in characteristics.items():
            # Try to map name to ID
            char_id = name_to_id.get(char_name)
            if not char_id:
                # Fallback: try direct lowercase match
                char_id = char_name.lower().replace(" ", "_")
                if char_id not in self.CHARACTERISTIC_ORDER:
                    char_id = char_name  # Use as-is

            score_value = score_data.get("score")
            reasoning = score_data.get("reasoning", "")

            if not isinstance(score_value, int) or not 1 <= score_value <= 5:
                raise ValueError(
                    f"Score for {char_name} must be 1-5, got: {score_value}"
                )

            scores.append(
                Score(
                    characteristic_id=char_id,
                    value=score_value,
                    reasoning=reasoning,
                )
            )

        # Validate all characteristics are present
        if len(scores) != len(self.CHARACTERISTIC_ORDER):
            found_ids = {s.characteristic_id for s in scores}
            missing = set(self.CHARACTERISTIC_ORDER) - found_ids
            raise ValueError(f"Missing characteristics in response: {missing}")

        return scores
