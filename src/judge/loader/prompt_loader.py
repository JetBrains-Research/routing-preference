"""Load and hydrate prompt templates."""

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
        "<CHARACTERISTIC_BASIS.md>": "basis",
        "<CHARACTERISTIC_SCORING_STEPS_V1.md>": "scoring_steps_v1",
        "<CHARACTERISTIC_SCORING_STEPS_V2.md>": "scoring_steps_v2",
    }

    def __init__(
        self,
        judge_dir: Path | None = None,
        characteristic_loader: CharacteristicLoader | None = None,
    ):
        self.judge_dir = judge_dir or self.DEFAULT_PATH
        self.char_loader = characteristic_loader or CharacteristicLoader(judge_dir=self.judge_dir)
        self._config: dict | None = None

    def _load_config(self) -> dict:
        """Load prompts.json configuration."""
        if self._config is None:
            config_path = self.judge_dir / "prompts.json"
            if config_path.exists():
                self._config = json.loads(config_path.read_text(encoding="utf-8"))
            else:
                self._config = {}
        return self._config

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path from prompts.json."""
        if relative_path.startswith("./"):
            return self.judge_dir / relative_path[2:]
        return Path(relative_path)

    def _get_prompt_path(self, prompt_type: str, version: str | None = None) -> Path:
        """Get the path to a prompt template."""
        config = self._load_config()

        # Use default version if not specified
        if version is None:
            version = config.get("defaults", {}).get(prompt_type, "V1")

        # Get path from config
        prompt_path = config.get("prompts", {}).get(prompt_type, {}).get(version)
        if prompt_path:
            return self._resolve_path(prompt_path)

        # Fallback
        return self.judge_dir / "prompts" / prompt_type / f"{version}.md"

    def load_single_prompt(
        self,
        characteristic_id: str,
        version: str | None = None,
    ) -> str:
        """Load and hydrate single-characteristic prompt template."""
        template_path = self._get_prompt_path("single", version)

        if not template_path.exists():
            raise ValueError(f"Prompt template not found: {template_path}")

        template = template_path.read_text(encoding="utf-8")
        char = self.char_loader.load(characteristic_id)
        return self._hydrate_single(template, char)

    def load_batch_prompt(
        self,
        characteristic_ids: list[str] | None = None,
        version: str | None = None,
    ) -> str:
        """Load and hydrate all-characteristics prompt template."""
        template_path = self._get_prompt_path("batch", version)

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
        for placeholder, attr in self.PLACEHOLDERS.items():
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
