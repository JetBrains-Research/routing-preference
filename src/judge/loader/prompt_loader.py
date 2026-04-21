"""Load and hydrate prompt templates.

Prompt paths follow a convention:
    ./prompts/{basis}/{granularity}/{exposure}.md

where:
    basis        in {"scoring", "ranking"}
    granularity  in {"all", "single"}
    exposure     in {"V1", "V2.0", "V2.1"}

Context templates are indexed by exposure in prompts.json under "exposure_context".
"""

import json
from pathlib import Path

from .characteristic_loader import CharacteristicLoader, LoadedCharacteristic


class PromptLoader:
    """Loads and hydrates prompt templates from docs/judge/prompts/."""

    DEFAULT_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "judge"

    PLACEHOLDERS = {
        "<CHARACTERISTIC_NAME.md>": "name",
        "<CHARACTERISTIC_SHORT.md>": "short_description",
        "<CHARACTERISTIC_LONG.md>": "long_description",
        "<CHARACTERISTIC_SCORING_BASIS.md>": "scoring_basis",
        "<CHARACTERISTIC_SCORING_STEPS_V1.md>": "scoring_steps_v1",
        "<CHARACTERISTIC_SCORING_STEPS_V2.md>": "scoring_steps_v2",
        "<CHARACTERISTIC_RANKING_BASIS.md>": "ranking_basis",
        "<CHARACTERISTIC_RANKING_STEPS_V1.md>": "ranking_steps_v1",
        "<CHARACTERISTIC_RANKING_STEPS_V2.md>": "ranking_steps_v2",
    }

    def __init__(
        self,
        judge_dir: Path | None = None,
        characteristic_loader: CharacteristicLoader | None = None,
    ):
        self.judge_dir = judge_dir or self.DEFAULT_PATH
        self.char_loader = characteristic_loader or CharacteristicLoader(
            judge_dir=self.judge_dir
        )
        self._config: dict | None = None

    def _load_config(self) -> dict:
        if self._config is None:
            config_path = self.judge_dir / "prompts.json"
            self._config = json.loads(config_path.read_text(encoding="utf-8"))
        return self._config

    def _resolve_path(self, relative_path: str) -> Path:
        if relative_path.startswith("./"):
            return self.judge_dir / relative_path[2:]
        return Path(relative_path)

    def _check_available(self, basis: str, granularity: str, exposure: str) -> None:
        available = self._load_config().get("available_prompts", {})
        exposures = available.get(basis, {}).get(granularity, [])
        if exposure not in exposures:
            raise ValueError(
                f"Prompt not available: {basis}/{granularity}/{exposure}. "
                f"Available: {exposures}"
            )

    def _prompt_path(self, basis: str, granularity: str, exposure: str) -> Path:
        self._check_available(basis, granularity, exposure)
        return self.judge_dir / "prompts" / basis / granularity / f"{exposure}.md"

    def load_single_prompt(
        self,
        basis: str,
        exposure: str,
        characteristic_id: str,
    ) -> str:
        """Load and hydrate a single-characteristic prompt template."""
        template_path = self._prompt_path(basis, "single", exposure)
        template = template_path.read_text(encoding="utf-8")
        char = self.char_loader.load(characteristic_id)
        return self._hydrate_single(template, char)

    def load_all_prompt(
        self,
        basis: str,
        exposure: str,
        characteristic_ids: list[str] | None = None,
    ) -> str:
        """Load and hydrate an all-characteristics prompt template."""
        template_path = self._prompt_path(basis, "all", exposure)
        template = template_path.read_text(encoding="utf-8")

        if characteristic_ids is None:
            characteristic_ids = self.char_loader.list_characteristics()

        chars = [self.char_loader.load(cid) for cid in characteristic_ids]
        return self._hydrate_all(template, chars)

    def load_context(self, basis: str, exposure: str) -> str:
        """Load the context template for a given basis and exposure."""
        mapping = self._load_config().get("exposure_context_version", {})
        version = mapping.get(exposure)
        if not version:
            raise ValueError(f"No context version configured for exposure: {exposure}")
        return (self.judge_dir / "context" / basis / f"{version}.md").read_text(
            encoding="utf-8"
        )

    def _hydrate_single(self, template: str, char: LoadedCharacteristic) -> str:
        result = template
        for placeholder, attr in self.PLACEHOLDERS.items():
            value = getattr(char, attr, "")
            result = result.replace(placeholder, value)
        return result

    def _hydrate_all(self, template: str, chars: list[LoadedCharacteristic]) -> str:
        result = template
        for i, char in enumerate(chars, 1):
            mappings = {
                f"<CHARACTERISTIC_{i}_NAME.md>": char.name,
                f"<CHARACTERISTIC_{i}_SHORT.md>": char.short_description,
                f"<CHARACTERISTIC_{i}_LONG.md>": char.long_description,
                f"<CHARACTERISTIC_{i}_SCORING_BASIS.md>": char.scoring_basis,
                f"<CHARACTERISTIC_{i}_SCORING_STEPS_V1.md>": char.scoring_steps_v1,
                f"<CHARACTERISTIC_{i}_SCORING_STEPS_V2.md>": char.scoring_steps_v2,
                f"<CHARACTERISTIC_{i}_RANKING_BASIS.md>": char.ranking_basis,
                f"<CHARACTERISTIC_{i}_RANKING_STEPS_V1.md>": char.ranking_steps_v1,
                f"<CHARACTERISTIC_{i}_RANKING_STEPS_V2.md>": char.ranking_steps_v2,
            }
            for placeholder, value in mappings.items():
                result = result.replace(placeholder, value)
        return result
