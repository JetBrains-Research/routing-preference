"""Load characteristics from docs/judge/characteristics/."""

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

    DEFAULT_PATH = (
        Path(__file__).parent.parent.parent.parent / "docs" / "judge" / "characteristics"
    )

    def __init__(self, characteristics_dir: Path | None = None):
        self.characteristics_dir = characteristics_dir or self.DEFAULT_PATH
        self._cache: dict[str, LoadedCharacteristic] = {}

    def list_characteristics(self) -> list[str]:
        """List available characteristic IDs."""
        if not self.characteristics_dir.exists():
            return []
        return sorted(
            d.name for d in self.characteristics_dir.iterdir() if d.is_dir()
        )

    def load(self, characteristic_id: str) -> LoadedCharacteristic:
        """Load a single characteristic by ID."""
        if characteristic_id in self._cache:
            return self._cache[characteristic_id]

        char_dir = self.characteristics_dir / characteristic_id
        if not char_dir.exists():
            raise ValueError(f"Characteristic not found: {characteristic_id}")

        prefix = characteristic_id.upper()

        char = LoadedCharacteristic(
            id=characteristic_id,
            name=self._load_file(char_dir / f"{prefix}_NAME.md"),
            short_description=self._load_file(char_dir / f"{prefix}_SHORT.md"),
            long_description=self._load_file(char_dir / f"{prefix}_LONG.md"),
            basis=self._load_file(char_dir / f"{prefix}_BASIS.md"),
            scoring_steps_v1=self._load_file(char_dir / f"{prefix}_SCORING_STEPS_V1.md"),
            scoring_steps_v2=self._load_file(char_dir / f"{prefix}_SCORING_STEPS_V2.md"),
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
