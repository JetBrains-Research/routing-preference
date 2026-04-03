"""Load characteristics from docs/judge/characteristics/."""

import json
from dataclasses import dataclass
from pathlib import Path

from .xml_parser import strip_xml_tags


@dataclass
class LoadedCharacteristic:
    """A characteristic loaded from docs/judge/characteristics/."""

    id: str
    name: str
    short_description: str
    long_description: str
    basis: str
    scoring_steps_v1: str
    scoring_steps_v2: str


class CharacteristicLoader:
    """Loads characteristics from docs/judge/characteristics/."""

    DEFAULT_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "judge"

    def __init__(self, judge_dir: Path | None = None):
        self.judge_dir = judge_dir or self.DEFAULT_PATH
        self._cache: dict[str, LoadedCharacteristic] = {}
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

    def list_characteristics(self) -> list[str]:
        """List available characteristic IDs."""
        config = self._load_config()
        if "characteristics" in config:
            return list(config["characteristics"].keys())
        return []

    def load(self, characteristic_id: str) -> LoadedCharacteristic:
        """Load a single characteristic by ID."""
        if characteristic_id in self._cache:
            return self._cache[characteristic_id]

        config = self._load_config()
        char_path = config.get("characteristics", {}).get(characteristic_id)

        if char_path:
            char_dir = self._resolve_path(char_path)
        else:
            char_dir = self.judge_dir / "characteristics" / characteristic_id

        if not char_dir.exists():
            raise ValueError(f"Characteristic not found: {characteristic_id}")

        prefix = characteristic_id.upper()
        char = LoadedCharacteristic(
            id=characteristic_id,
            name=self._load_file(char_dir / f"{prefix}_NAME.md"),
            short_description=self._load_file(char_dir / f"{prefix}_SHORT.md"),
            long_description=self._load_file(char_dir / f"{prefix}_LONG.md"),
            basis=self._load_file(char_dir / f"{prefix}_BASIS.md"),
            scoring_steps_v1=self._load_file(
                char_dir / f"{prefix}_SCORING_STEPS_V1.md"
            ),
            scoring_steps_v2=self._load_file(
                char_dir / f"{prefix}_SCORING_STEPS_V2.md"
            ),
        )

        self._cache[characteristic_id] = char
        return char

    def load_all(self) -> list[LoadedCharacteristic]:
        """Load all characteristics."""
        return [self.load(cid) for cid in self.list_characteristics()]

    def _load_file(self, path: Path) -> str:
        """Load and strip XML tags from a file."""
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8")
        return strip_xml_tags(content)
