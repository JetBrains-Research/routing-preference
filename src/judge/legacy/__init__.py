"""Legacy code - deprecated, kept for backward compatibility."""

from .characteristics import CHARACTERISTICS, get_characteristic
from .scorer import CharacteristicScorer
from ..models import Characteristic

__all__ = ["Characteristic", "CHARACTERISTICS", "CharacteristicScorer", "get_characteristic"]
