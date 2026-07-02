"""Tests for strict validation of batch judge responses."""

import json

import pytest

from src.judge.ranking.v1.ranker import Ranker as V1Ranker
from src.judge.ranking.v2.ranker import Ranker as V2Ranker
from src.judge.scoring.v1.scorer import Scorer as V1Scorer
from src.judge.scoring.v2.scorer import Scorer as V2Scorer

SOLUTION_IDS = [f"model_{i}__run_{i}" for i in range(7)]


def _scoring_response(char_keys):
    return json.dumps(
        {
            "characteristics": {
                key: {"score": 3, "reasoning": "r"} for key in char_keys
            }
        }
    )


def _ranking_response(char_keys):
    ranking = [
        {"rank": rank, "solution_id": f"sol_{rank}"} for rank in range(1, 8)
    ]
    return json.dumps(
        {"characteristics": {key: {"ranking": ranking} for key in char_keys}}
    )


@pytest.fixture(params=["v1", "v2"])
def scorer(request):
    if request.param == "v1":
        return V1Scorer()
    return V2Scorer(exposure="V2.1")


@pytest.fixture(params=["v1", "v2"])
def ranker(request):
    if request.param == "v1":
        return V1Ranker()
    return V2Ranker(exposure="V2.1")


def test_scorer_accepts_ids_and_display_names(scorer):
    ids = scorer.characteristic_order
    scores = scorer._parse_all_response(_scoring_response(ids))
    assert {s.characteristic_id for s in scores} == set(ids)

    names = [scorer.char_loader.load(cid).name for cid in ids]
    scores = scorer._parse_all_response(_scoring_response(names))
    assert {s.characteristic_id for s in scores} == set(ids)


def test_scorer_rejects_unknown_characteristic(scorer):
    keys = list(scorer.characteristic_order)
    keys[0] = "Creativity"
    with pytest.raises(ValueError, match="Unknown characteristic"):
        scorer._parse_all_response(_scoring_response(keys))


def test_scorer_rejects_missing_characteristic(scorer):
    keys = list(scorer.characteristic_order)[:-1]
    with pytest.raises(ValueError, match="Missing characteristics"):
        scorer._parse_all_response(_scoring_response(keys))


def test_scorer_rejects_duplicate_by_alias(scorer):
    first_id = scorer.characteristic_order[0]
    first_name = scorer.char_loader.load(first_id).name
    keys = [first_name, *scorer.characteristic_order]
    with pytest.raises(ValueError, match="Duplicate characteristic"):
        scorer._parse_all_response(_scoring_response(keys))


def test_ranker_accepts_ids(ranker):
    ids = ranker.characteristic_order
    results = ranker._parse_all_response(_ranking_response(ids), SOLUTION_IDS)
    assert {r.characteristic_id for r in results} == set(ids)
    assert all(len(r.rankings) == 7 for r in results)


def test_ranker_rejects_unknown_characteristic(ranker):
    keys = list(ranker.characteristic_order)
    keys[0] = "Creativity"
    with pytest.raises(ValueError, match="Unknown characteristic"):
        ranker._parse_all_response(_ranking_response(keys), SOLUTION_IDS)


def test_ranker_rejects_missing_characteristic(ranker):
    keys = list(ranker.characteristic_order)[:-1]
    with pytest.raises(ValueError, match="Missing characteristics"):
        ranker._parse_all_response(_ranking_response(keys), SOLUTION_IDS)
