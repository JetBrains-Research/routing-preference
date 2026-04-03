"""LLM as a Judge"""

# New prompt-based system
from .batch_scorer import BatchScorer
from .judge import Judge, ScoringMode
from .loader import CharacteristicLoader, LoadedCharacteristic, PromptLoader
from .models import Characteristic, Judgment, Score
from .prompt_scorer import PromptScorer
from .storage import JudgmentStorage

# Ranking (unchanged)
from .ranking_judge import RankingJudge
from .ranking_models import ComparativeJudgment, Ranking
from .ranking_storage import RankingStorage

# Legacy (deprecated, kept for ranking mode)
from .characteristics import CHARACTERISTICS, get_characteristic
from .scorer import CharacteristicScorer

__all__ = [
    # New
    "BatchScorer",
    "CharacteristicLoader",
    "Judge",
    "LoadedCharacteristic",
    "PromptLoader",
    "PromptScorer",
    "ScoringMode",
    # Models
    "Characteristic",
    "Judgment",
    "JudgmentStorage",
    "Score",
    # Ranking
    "ComparativeJudgment",
    "Ranking",
    "RankingJudge",
    "RankingStorage",
    # Legacy
    "CHARACTERISTICS",
    "CharacteristicScorer",
    "get_characteristic",
]
