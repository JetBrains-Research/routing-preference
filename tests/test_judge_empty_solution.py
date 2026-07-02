"""Empty-diff solutions must be scored without any LLM call."""

import pytest

from src.judge.judge import Judge
from src.models import Issue, Solution


@pytest.fixture(autouse=True)
def no_llm_calls(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("LLM must not be called for empty solutions")

    monkeypatch.setattr("litellm.completion", fail)


def _issue():
    return Issue(issue_id="issue-1", repo="r/r", number=1, title="t", body="b")


def _empty_solution():
    return Solution(
        issue_id="issue-1",
        model="m/model",
        provider="m",
        diff="  \n",
        trajectory={},
        duration_ms=1,
        created_at="now",
    )


@pytest.mark.parametrize("exposure", ["V1", "V2.1"])
def test_score_skips_llm_for_empty_diff(exposure):
    judge = Judge(model="judge/model", exposure=exposure)
    judgment = judge.score(_issue(), _empty_solution(), "folder")

    assert judgment.empty_solution is True
    assert judgment.overall_score == 1.0
    assert [s.value for s in judgment.scores] == [1, 1, 1, 1]


def test_score_single_skips_llm_for_empty_diff():
    judge = Judge(model="judge/model", exposure="V1")
    judgment = judge.score_single(_issue(), _empty_solution(), "folder")

    assert judgment.empty_solution is True
    assert judgment.granularity == "single"
    assert [s.value for s in judgment.scores] == [1, 1, 1, 1]
