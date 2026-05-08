"""Selection configuration loading and validation."""

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_SELECTION_CONFIG_PATH = PROJECT_ROOT / "configs" / "selection.json"


@dataclass(frozen=True)
class SelectionConfig:
    """Parameters that control pair selection."""

    max_average_gap: float = 0.75
    min_subscore_diversity: float = 0.0
    local_pair_quality_weight: float = 1.0
    model_coverage_weight: float = 0.4
    model_balance_weight: float = 0.3
    quality_band_balance_weight: float = 0.0
    fallback_if_no_feasible_pair: str = "best_local"
    quality_bands: dict[str, tuple[float, float]] | None = None


def load_selection_config(path: Path | None = None) -> SelectionConfig:
    """Load selection config from JSON."""
    config_path = path or DEFAULT_SELECTION_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Selection config not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return selection_config_from_dict(data)


def selection_config_from_dict(data: dict) -> SelectionConfig:
    """Build and validate a SelectionConfig from raw JSON data."""
    if "quality_bands" not in data:
        raise ValueError("quality_bands must be defined in selection config")

    config = SelectionConfig(
        max_average_gap=float(data.get("max_average_gap", 0.75)),
        min_subscore_diversity=float(data.get("min_subscore_diversity", 0.0)),
        local_pair_quality_weight=float(data.get("local_pair_quality_weight", 1.0)),
        model_coverage_weight=float(data.get("model_coverage_weight", 0.4)),
        model_balance_weight=float(data.get("model_balance_weight", 0.3)),
        quality_band_balance_weight=float(
            data.get("quality_band_balance_weight", 0.0)
        ),
        fallback_if_no_feasible_pair=str(
            data.get("fallback_if_no_feasible_pair", "best_local")
        ),
        quality_bands=_parse_quality_bands(data["quality_bands"]),
    )
    _validate_config(config)
    return config


def _parse_quality_bands(raw: dict) -> dict[str, tuple[float, float]]:
    bands = {}
    for name, bounds in raw.items():
        if not isinstance(bounds, list | tuple) or len(bounds) != 2:
            raise ValueError(f"Quality band {name!r} must have two bounds")
        bands[str(name)] = (float(bounds[0]), float(bounds[1]))
    return bands


def _validate_config(config: SelectionConfig) -> None:
    if config.max_average_gap < 0:
        raise ValueError("max_average_gap must be non-negative")
    if config.min_subscore_diversity < 0:
        raise ValueError("min_subscore_diversity must be non-negative")
    if config.fallback_if_no_feasible_pair != "best_local":
        raise ValueError("fallback_if_no_feasible_pair must be 'best_local'")

    weights = {
        "local_pair_quality_weight": config.local_pair_quality_weight,
        "model_coverage_weight": config.model_coverage_weight,
        "model_balance_weight": config.model_balance_weight,
        "quality_band_balance_weight": config.quality_band_balance_weight,
    }
    for name, value in weights.items():
        if value < 0:
            raise ValueError(f"{name} must be non-negative")

    if not config.quality_bands:
        raise ValueError("quality_bands must not be empty")

    for name, (lower, upper) in config.quality_bands.items():
        if lower >= upper:
            raise ValueError(
                f"Quality band {name!r} lower bound must be below upper bound"
            )
