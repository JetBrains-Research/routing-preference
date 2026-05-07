"""V1 ranking - issue + diffs only."""

import json

import litellm

from ....models import Issue, Solution
from ...loader import CharacteristicLoader, PromptLoader
from ...models import CharacteristicRanking, Ranking

CHARACTERISTIC_ORDER = ["intent", "correctness", "scope", "quality"]
N_SOLUTIONS = 7


class Ranker:
    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model
        self.char_loader = CharacteristicLoader()
        self.prompt_loader = PromptLoader(characteristic_loader=self.char_loader)

    def rank_all(
        self,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
    ) -> list[CharacteristicRanking]:
        """Rank N solutions on all characteristics in a single LLM call."""
        self._validate(solutions, solution_ids)
        prompt = self._build_all_prompt(issue, solutions, solution_ids)
        response = self._call_llm(prompt)
        return self._parse_all_response(response, solution_ids)

    def rank_single(
        self,
        characteristic_id: str,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
    ) -> CharacteristicRanking:
        """Rank N solutions on a single characteristic."""
        self._validate(solutions, solution_ids)
        prompt = self._build_single_prompt(
            characteristic_id, issue, solutions, solution_ids
        )
        response = self._call_llm(prompt)
        return self._parse_single_response(response, characteristic_id, solution_ids)

    def _validate(
        self, solutions: list[Solution], solution_ids: list[str]
    ) -> None:
        if len(solutions) != N_SOLUTIONS:
            raise ValueError(
                f"Ranking requires exactly {N_SOLUTIONS} solutions, got {len(solutions)}"
            )
        if len(solution_ids) != N_SOLUTIONS:
            raise ValueError(
                f"Expected {N_SOLUTIONS} solution_ids, got {len(solution_ids)}"
            )
        if len(set(solution_ids)) != N_SOLUTIONS:
            raise ValueError("solution_ids must be unique")

    @staticmethod
    def _short_id(index: int) -> str:
        """Short, unambiguous identifier used in prompts."""
        return f"sol_{index + 1}"

    def _build_context(
        self,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
    ) -> str:
        context = self.prompt_loader.load_context(basis="ranking", exposure="V1")
        context = context.replace("<ISSUE_TITLE>", issue.title)
        context = context.replace("<ISSUE_BODY>", issue.body)
        for i, sol in enumerate(solutions, start=1):
            context = context.replace(f"<SOLUTION_{i}_ID>", self._short_id(i - 1))
            context = context.replace(f"<SOLUTION_{i}_DIFF>", sol.diff)
        return context

    def _build_all_prompt(
        self,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
    ) -> str:
        template = self.prompt_loader.load_all_prompt(
            basis="ranking",
            exposure="V1",
            characteristic_ids=CHARACTERISTIC_ORDER,
        )
        return (
            template + "\n\n" + self._build_context(issue, solutions, solution_ids)
        )

    def _build_single_prompt(
        self,
        characteristic_id: str,
        issue: Issue,
        solutions: list[Solution],
        solution_ids: list[str],
    ) -> str:
        template = self.prompt_loader.load_single_prompt(
            basis="ranking",
            exposure="V1",
            characteristic_id=characteristic_id,
        )
        return (
            template + "\n\n" + self._build_context(issue, solutions, solution_ids)
        )

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

    def _parse_ranking_list(
        self,
        ranking_data: list,
        short_to_real: dict[str, str],
    ) -> list[Ranking]:
        if not isinstance(ranking_data, list):
            raise ValueError(f"Expected ranking list, got: {type(ranking_data)}")
        if len(ranking_data) != N_SOLUTIONS:
            raise ValueError(
                f"Expected {N_SOLUTIONS} ranking entries, got {len(ranking_data)}"
            )

        rankings = []
        seen_ranks = set()
        seen_ids = set()
        for entry in ranking_data:
            rank = entry.get("rank")
            short_id = entry.get("solution_id")
            if not isinstance(rank, int) or not 1 <= rank <= N_SOLUTIONS:
                raise ValueError(f"Invalid rank: {rank}")
            if rank in seen_ranks:
                raise ValueError(f"Duplicate rank: {rank}")
            if short_id not in short_to_real:
                raise ValueError(f"Unknown solution_id: {short_id}")
            if short_id in seen_ids:
                raise ValueError(f"Duplicate solution_id: {short_id}")
            seen_ranks.add(rank)
            seen_ids.add(short_id)
            rankings.append(Ranking(rank=rank, solution_id=short_to_real[short_id]))

        return rankings

    def _short_to_real_map(self, solution_ids: list[str]) -> dict[str, str]:
        return {self._short_id(i): sid for i, sid in enumerate(solution_ids)}

    def _parse_single_response(
        self,
        response: str,
        characteristic_id: str,
        solution_ids: list[str],
    ) -> CharacteristicRanking:
        data = json.loads(response)
        rankings = self._parse_ranking_list(
            data.get("ranking", []), self._short_to_real_map(solution_ids)
        )
        return CharacteristicRanking(
            characteristic_id=characteristic_id, rankings=rankings
        )

    def _parse_all_response(
        self,
        response: str,
        solution_ids: list[str],
    ) -> list[CharacteristicRanking]:
        data = json.loads(response)
        characteristics = data.get("characteristics", {})

        name_to_id = {}
        for cid in CHARACTERISTIC_ORDER:
            char = self.char_loader.load(cid)
            name_to_id[char.name] = cid

        short_to_real = self._short_to_real_map(solution_ids)
        results = []
        for char_name, char_data in characteristics.items():
            char_id = name_to_id.get(char_name)
            if not char_id:
                char_id = char_name.lower().replace(" ", "_")
                if char_id not in CHARACTERISTIC_ORDER:
                    char_id = char_name

            rankings = self._parse_ranking_list(
                char_data.get("ranking", []), short_to_real
            )
            results.append(
                CharacteristicRanking(characteristic_id=char_id, rankings=rankings)
            )

        if len(results) != len(CHARACTERISTIC_ORDER):
            found_ids = {r.characteristic_id for r in results}
            missing = set(CHARACTERISTIC_ORDER) - found_ids
            raise ValueError(f"Missing characteristics in response: {missing}")

        return results
