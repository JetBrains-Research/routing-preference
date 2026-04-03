"""Load and hydrate prompt templates."""

from pathlib import Path

from .characteristic_loader import CharacteristicLoader, LoadedCharacteristic


class PromptLoader:
    """Loads and hydrates prompt templates from docs/judge/prompts/."""

    DEFAULT_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "judge" / "prompts"

    # Single characteristic placeholders
    SINGLE_PLACEHOLDERS = {
        "<CHARACTERISTIC_NAME.md>": "name",
        "<CHARACTERISTIC_SHORT.md>": "short_description",
        "<CHARACTERISTIC_LONG.md>": "long_description",
        "<CHARACTERISTIC_BASIS.md>": "basis",
        "<CHARACTERISTIC_SCORING_STEPS_V1.md>": "scoring_steps_v1",
        "<CHARACTERISTIC_SCORING_STEPS_V2.md>": "scoring_steps_v2",
    }

    def __init__(
        self,
        prompts_dir: Path | None = None,
        characteristic_loader: CharacteristicLoader | None = None,
    ):
        self.prompts_dir = prompts_dir or self.DEFAULT_PATH
        self.char_loader = characteristic_loader or CharacteristicLoader()

    def load_single_prompt(
        self,
        characteristic_id: str,
        version: str = "V2.1",
    ) -> str:
        """Load and hydrate single-characteristic prompt template."""
        template_path = self.prompts_dir / f"JUDGE_SCORING_PROMPT_{version}.md"
        if not template_path.exists():
            raise ValueError(f"Prompt template not found: {template_path}")
        template = template_path.read_text(encoding="utf-8")

        char = self.char_loader.load(characteristic_id)
        return self._hydrate_single(template, char)

    def load_batch_prompt(
        self,
        characteristic_ids: list[str] | None = None,
        version: str = "V1",
    ) -> str:
        """Load and hydrate all-characteristics prompt template."""
        template_path = self.prompts_dir / f"JUDGE_SCORING_ALL_PROMPT_{version}.md"
        if not template_path.exists():
            raise ValueError(f"Prompt template not found: {template_path}")
        template = template_path.read_text(encoding="utf-8")

        if characteristic_ids is None:
            characteristic_ids = self.char_loader.list_characteristics()

        chars = [self.char_loader.load(cid) for cid in characteristic_ids]
        return self._hydrate_batch(template, chars)

    def _hydrate_single(self, template: str, char: LoadedCharacteristic) -> str:
        """Replace single-characteristic placeholders."""
        result = template
        for placeholder, attr in self.SINGLE_PLACEHOLDERS.items():
            value = getattr(char, attr, "")
            result = result.replace(placeholder, value)
        return result

    def _hydrate_batch(self, template: str, chars: list[LoadedCharacteristic]) -> str:
        """Replace numbered characteristic placeholders."""
        result = template

        for i, char in enumerate(chars, 1):
            mappings = {
                f"<CHARACTERISTIC_{i}_NAME.md>": char.name,
                f"<CHARACTERISTIC_{i}_SHORT.md>": char.short_description,
                f"<CHARACTERISTIC_{i}_LONG.md>": char.long_description,
                f"<CHARACTERISTIC_{i}_BASIS.md>": char.basis,
                f"<CHARACTERISTIC_{i}_SCORING_STEPS_V1.md>": char.scoring_steps_v1,
                f"<CHARACTERISTIC_{i}_SCORING_STEPS_V2.md>": char.scoring_steps_v2,
            }
            for placeholder, value in mappings.items():
                result = result.replace(placeholder, value)

        return result
