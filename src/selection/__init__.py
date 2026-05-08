"""Solution selection."""

from .balanced import (
    BalancedSelectionResult,
    IssueSelection,
    ScoredCandidate,
    select_balanced_pairs,
)
from .config import SelectionConfig, load_selection_config
from .cpsat import select_balanced_pairs_cpsat
from .models import SelectedPair, SelectedSolution
from .selector import (
    CHARACTERISTIC_ORDER,
    CandidatePair,
    ScoredSolution,
    generate_candidate_pairs,
    select_best_pair,
)
from .storage import (
    SelectionStorage,
    generate_candidates_for_issue,
    load_scored_solutions,
    select_pair_for_issue,
    selection_run_id,
    selection_source_run_id,
)

__all__ = [
    "CHARACTERISTIC_ORDER",
    "CandidatePair",
    "BalancedSelectionResult",
    "IssueSelection",
    "ScoredSolution",
    "ScoredCandidate",
    "SelectedPair",
    "SelectedSolution",
    "SelectionConfig",
    "SelectionStorage",
    "generate_candidate_pairs",
    "generate_candidates_for_issue",
    "load_scored_solutions",
    "load_selection_config",
    "select_best_pair",
    "select_balanced_pairs",
    "select_balanced_pairs_cpsat",
    "select_pair_for_issue",
    "selection_source_run_id",
    "selection_run_id",
]
