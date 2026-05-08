"""Load and hydrate prompt templates configured in docs/judge/prompts.json."""

import json
from pathlib import Path

from .characteristic_loader import CharacteristicLoader, LoadedCharacteristic


class PromptLoader:
    """Loads and hydrates prompt templates configured in docs/judge/prompts.json."""

    DEFAULT_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "judge"

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
        path = Path(relative_path)
        if path.is_absolute():
            return path
        if relative_path.startswith("./"):
            return self.judge_dir / relative_path[2:]
        return self.judge_dir / path

    def _prompt_path(self, basis: str, granularity: str, exposure: str) -> Path:
        prompts = self._load_config().get("prompts", {})
        relative_path = prompts.get(basis, {}).get(granularity, {}).get(exposure)
        if not relative_path:
            available = sorted(prompts.get(basis, {}).get(granularity, {}).keys())
            raise ValueError(
                f"Prompt not configured: {basis}/{granularity}/{exposure}. "
                f"Available: {available}"
            )
        return self._resolve_path(relative_path)

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
        contexts = self._load_config().get("contexts", {})
        relative_path = contexts.get(basis, {}).get(exposure)
        if not relative_path:
            available = sorted(contexts.get(basis, {}).keys())
            raise ValueError(
                f"Context not configured: {basis}/{exposure}. "
                f"Available: {available}"
            )
        return self._resolve_path(relative_path).read_text(encoding="utf-8")

    def _placeholder_fields(self) -> dict[str, str]:
        fields = self._load_config().get("characteristic_placeholders", {})
        if not fields:
            raise ValueError("No characteristic_placeholders configured")
        return fields

    def _hydrate_single(self, template: str, char: LoadedCharacteristic) -> str:
        result = template
        for placeholder_key, attr in self._placeholder_fields().items():
            value = getattr(char, attr, "")
            placeholder = f"<{placeholder_key}>"
            result = result.replace(placeholder, value)
        return result

    def _hydrate_all(self, template: str, chars: list[LoadedCharacteristic]) -> str:
        result = template
        placeholder_fields = self._placeholder_fields()
        for i, char in enumerate(chars, 1):
            for placeholder_key, attr in placeholder_fields.items():
                numbered_key = placeholder_key.replace(
                    "CHARACTERISTIC_",
                    f"CHARACTERISTIC_{i}_",
                    1,
                )
                placeholder = f"<{numbered_key}>"
                value = getattr(char, attr, "")
                result = result.replace(placeholder, value)
        return result
