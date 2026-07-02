"""Tests for single-pass prompt template substitution."""

from src.templating import fill_template


def test_replaces_all_placeholders():
    result = fill_template(
        "T: <ISSUE_TITLE>\nB: <ISSUE_BODY>",
        {"<ISSUE_TITLE>": "title", "<ISSUE_BODY>": "body"},
    )
    assert result == "T: title\nB: body"


def test_inserted_content_is_not_rescanned():
    body = "see <SOLUTION_DIFF> for details"
    result = fill_template(
        "B: <ISSUE_BODY>\nD: <SOLUTION_DIFF>",
        {"<ISSUE_BODY>": body, "<SOLUTION_DIFF>": "the diff"},
    )
    assert result == "B: see <SOLUTION_DIFF> for details\nD: the diff"


def test_values_containing_other_placeholders_stay_literal():
    result = fill_template(
        "1: <SOLUTION_1_DIFF>\n2: <SOLUTION_2_DIFF>",
        {
            "<SOLUTION_1_DIFF>": "diff with <SOLUTION_2_DIFF> inside",
            "<SOLUTION_2_DIFF>": "second diff",
        },
    )
    assert result == "1: diff with <SOLUTION_2_DIFF> inside\n2: second diff"


def test_backslashes_in_values_are_preserved():
    result = fill_template(
        "D: <SOLUTION_DIFF>",
        {"<SOLUTION_DIFF>": r"a \1 \g<0> backslash"},
    )
    assert result == r"D: a \1 \g<0> backslash"


def test_empty_values_returns_template():
    assert fill_template("unchanged <X>", {}) == "unchanged <X>"


def test_repeated_placeholder_replaced_everywhere():
    result = fill_template(
        "<ISSUE_TITLE> and <ISSUE_TITLE>",
        {"<ISSUE_TITLE>": "t"},
    )
    assert result == "t and t"
