"""Load characteristic fragments configured in docs/judge/prompts.json."""

import json
from dataclasses import dataclass
from pathlib import Path

from .xml_parser import strip_xml_tags


@dataclass
class LoadedCharacteristic:
    """A characteristic loaded from configured Markdown fragments."""

    id: str
    name: str
    short_description: str
    long_description: str
    scoring_basis: str
    scoring_steps_v1: str
    scoring_steps_v2: str
    ranking_basis: str
    ranking_steps_v1: str
    ranking_steps_v2: str


class CharacteristicLoader:
    """Loads characteristics through docs/judge/prompts.json."""

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

    def list_characteristics(self) -> list[str]:
        """List available characteristic IDs."""
        return list(self._load_config().get("characteristics", []))

    def _resolve_path(self, relative_path: str) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            return path
        if relative_path.startswith("./"):
            return self.judge_dir / relative_path[2:]
        return self.judge_dir / path

    def load(self, characteristic_id: str) -> LoadedCharacteristic:
        """Load a single characteristic by ID."""
        if characteristic_id in self._cache:
            return self._cache[characteristic_id]

        config = self._load_config()
        paths = config.get("characteristic_paths", {})
        if characteristic_id not in paths:
            raise ValueError(f"Characteristic not configured: {characteristic_id}")
        char_dir = self._resolve_path(paths[characteristic_id])
        if not char_dir.exists():
            raise ValueError(f"Characteristic not found: {characteristic_id}")

        files = config.get("characteristic_files", {})
        char = LoadedCharacteristic(
            id=characteristic_id,
            name=self._load_file(char_dir / files["name"]),
            short_description=self._load_file(char_dir / files["short_description"]),
            long_description=self._load_file(char_dir / files["long_description"]),
            scoring_basis=self._load_file(char_dir / files["scoring_basis"]),
            scoring_steps_v1=self._load_file(char_dir / files["scoring_steps_v1"]),
            scoring_steps_v2=self._load_file(char_dir / files["scoring_steps_v2"]),
            ranking_basis=self._load_file(char_dir / files["ranking_basis"]),
            ranking_steps_v1=self._load_file(char_dir / files["ranking_steps_v1"]),
            ranking_steps_v2=self._load_file(char_dir / files["ranking_steps_v2"]),
        )

        self._cache[characteristic_id] = char
        return char

    def _load_file(self, path: Path) -> str:
        """Load and strip XML tags from a file."""
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8")
        return strip_xml_tags(content)
