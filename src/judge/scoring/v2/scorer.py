"""V2 scoring."""

import json

import litellm

from ....models import Issue, Solution
from ...loader import CharacteristicLoader, PromptLoader
from ...models import Score

CHARACTERISTIC_ORDER = ["intent", "correctness", "scope", "quality"]


class Scorer:
    def __init__(self, model: str = "openai/gpt-4o", prompt_version: str = "V2.1"):
        self.model = model
        self.prompt_version = prompt_version
        self.char_loader = CharacteristicLoader()
        self.prompt_loader = PromptLoader(characteristic_loader=self.char_loader)

    def score_all(
        self,
        issue: Issue,
        solution: Solution,
        source_files: dict[str, str],
    ) -> list[Score]:
        """Score all characteristics in a single call."""
        prompt = self._build_batch_prompt(issue, solution, source_files)
        response = self._call_llm(prompt)
        return self._parse_batch_response(response)

    def score_single(
        self,
        characteristic_id: str,
        issue: Issue,
        solution: Solution,
        source_files: dict[str, str],
    ) -> Score:
        """Score a single characteristic."""
        prompt = self._build_single_prompt(characteristic_id, issue, solution, source_files)
        response = self._call_llm(prompt)
        return self._parse_single_response(response, characteristic_id)

    def _build_context(
        self,
        issue: Issue,
        solution: Solution,
        source_files: dict[str, str],
    ) -> str:
        context = self.prompt_loader.load_context(version="V2")
        context = context.replace("<ISSUE_TITLE>", issue.title)
        context = context.replace("<ISSUE_BODY>", issue.body)
        context = context.replace("<SOURCE_FILES>", self._format_source_files(source_files))
        context = context.replace("<SOLUTION_DIFF>", solution.diff)
        return context

    def _build_batch_prompt(
        self,
        issue: Issue,
        solution: Solution,
        source_files: dict[str, str],
    ) -> str:
        template = self.prompt_loader.load_batch_prompt(
            characteristic_ids=CHARACTERISTIC_ORDER,
            version="V1",
        )
        return template + "\n\n" + self._build_context(issue, solution, source_files)

    def _build_single_prompt(
        self,
        characteristic_id: str,
        issue: Issue,
        solution: Solution,
        source_files: dict[str, str],
    ) -> str:
        template = self.prompt_loader.load_single_prompt(
            characteristic_id=characteristic_id,
            version=self.prompt_version,
        )
        return template + "\n\n" + self._build_context(issue, solution, source_files)

    def _format_source_files(self, source_files: dict[str, str]) -> str:
        if not source_files:
            return "(No source files provided)"

        parts = []
        for filepath, content in source_files.items():
            parts.append(f"### {filepath}\n```\n{content}\n```")
        return "\n\n".join(parts)

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

    def _parse_single_response(self, response: str, characteristic_id: str) -> Score:
        data = json.loads(response)
        score_value = data.get("score")
        reasoning = data.get("reasoning", "")

        if not isinstance(score_value, int) or not 1 <= score_value <= 5:
            raise ValueError(f"Score must be 1-5, got: {score_value}")

        return Score(
            characteristic_id=characteristic_id,
            value=score_value,
            reasoning=reasoning,
        )

    def _parse_batch_response(self, response: str) -> list[Score]:
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
