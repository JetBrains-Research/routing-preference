"""V1 scoring - issue + diff only, no source files."""

import json

import litellm

from ....models import Issue, Solution
from ...loader import CharacteristicLoader, PromptLoader
from ...models import Score

CHARACTERISTIC_ORDER = ["intent", "correctness", "scope", "quality"]


class Scorer:
    """V1 scorer - scores using issue + diff only."""

    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model
        self.char_loader = CharacteristicLoader()
        self.prompt_loader = PromptLoader(characteristic_loader=self.char_loader)

    def score_all(self, issue: Issue, solution: Solution) -> list[Score]:
        """Score all characteristics in a single LLM call."""
        prompt = self._build_prompt(issue, solution)
        response = self._call_llm(prompt)
        return self._parse_response(response)

    def _build_prompt(self, issue: Issue, solution: Solution) -> str:
        template = self.prompt_loader.load_batch_prompt(
            characteristic_ids=CHARACTERISTIC_ORDER,
            version="V1",
        )
        context = self.prompt_loader.load_context(version="V1")
        context = context.replace("<ISSUE_TITLE>", issue.title)
        context = context.replace("<ISSUE_BODY>", issue.body)
        context = context.replace("<SOLUTION_DIFF>", solution.diff)
        return template + "\n\n" + context

    def _call_llm(self, prompt: str) -> str:
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
        data = json.loads(response)
        characteristics = data.get("characteristics", {})
        scores = []

        name_to_id = {}
        for cid in CHARACTERISTIC_ORDER:
            char = self.char_loader.load(cid)
            name_to_id[char.name] = cid

        for char_name, score_data in characteristics.items():
            char_id = name_to_id.get(char_name)
            if not char_id:
                char_id = char_name.lower().replace(" ", "_")
                if char_id not in CHARACTERISTIC_ORDER:
                    char_id = char_name

            score_value = score_data.get("score")
            reasoning = score_data.get("reasoning", "")

            if not isinstance(score_value, int) or not 1 <= score_value <= 5:
                raise ValueError(f"Score for {char_name} must be 1-5, got: {score_value}")

            scores.append(Score(
                characteristic_id=char_id,
                value=score_value,
                reasoning=reasoning,
            ))

        if len(scores) != len(CHARACTERISTIC_ORDER):
            found_ids = {s.characteristic_id for s in scores}
            missing = set(CHARACTERISTIC_ORDER) - found_ids
            raise ValueError(f"Missing characteristics in response: {missing}")

        return scores
