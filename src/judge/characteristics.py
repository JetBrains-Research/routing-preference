"""Characteristic definitions for the judge"""

from .models import Characteristic

# Base prompt structure shared by all characteristics
_BASE_PROMPT = """You are evaluating a code solution for a GitHub issue.

## Issue
**Title:** {issue_title}

**Description:**
{issue_body}

## Solution (git diff)
```diff
{diff}
```

## Task
{task_description}

## Response Format
Respond with ONLY the following format:
Score: <number 1-10>
Reasoning: <your explanation>
"""

CHARACTERISTICS: list[Characteristic] = [
    Characteristic(
        id="correctness",
        name="Code Correctness",
        description="Does the solution correctly solve the issue?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the CORRECTNESS of this solution.
- Does the code change correctly address the issue described?
- Will the solution work as intended?
- Are there any bugs or logical errors?

Score 1-10 where:
- 1-3: Solution is incorrect or introduces bugs
- 4-6: Partially correct but has issues
- 7-9: Correct solution with minor issues
- 10: Perfect, fully correct solution""",
        ),
    ),
    Characteristic(
        id="completeness",
        name="Solution Completeness",
        description="Does the solution address all aspects of the issue?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the COMPLETENESS of this solution.
- Does it address all aspects mentioned in the issue?
- Are edge cases handled?
- Is anything missing that should be included?

Score 1-10 where:
- 1-3: Major parts of the issue are not addressed
- 4-6: Addresses main issue but misses some aspects
- 7-9: Addresses most or all aspects
- 10: Fully complete, handles all cases""",
        ),
    ),
    Characteristic(
        id="readability",
        name="Code Readability",
        description="Is the code easy to read and understand?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the READABILITY of this solution.
- Is the code easy to read and understand?
- Are variable/function names clear and descriptive?
- Is the code structure logical and easy to follow?

Score 1-10 where:
- 1-3: Very hard to read, confusing code
- 4-6: Somewhat readable but could be clearer
- 7-9: Clear and easy to understand
- 10: Exceptionally readable and well-structured""",
        ),
    ),
    Characteristic(
        id="maintainability",
        name="Maintainability",
        description="Is the code well-structured and maintainable?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the MAINTAINABILITY of this solution.
- Is the code modular and well-organized?
- Would it be easy for another developer to modify?
- Does it follow good software engineering practices?

Score 1-10 where:
- 1-3: Hard to maintain, tightly coupled, poor structure
- 4-6: Some maintainability concerns
- 7-9: Well-structured and maintainable
- 10: Excellent structure, very easy to maintain""",
        ),
    ),
    Characteristic(
        id="efficiency",
        name="Efficiency",
        description="Is the solution performant and resource-efficient?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the EFFICIENCY of this solution.
- Is the solution performant?
- Are there any unnecessary operations or redundant code?
- Does it use appropriate data structures and algorithms?

Score 1-10 where:
- 1-3: Inefficient, performance issues
- 4-6: Acceptable but could be optimized
- 7-9: Efficient solution
- 10: Optimally efficient""",
        ),
    ),
    Characteristic(
        id="safety",
        name="Code Safety",
        description="Does the code avoid security vulnerabilities and handle edge cases?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the SAFETY of this solution.
- Does the code avoid security vulnerabilities?
- Are edge cases and error conditions handled?
- Is input validation appropriate?

Score 1-10 where:
- 1-3: Security issues or unhandled edge cases
- 4-6: Some safety concerns
- 7-9: Safe and handles most edge cases
- 10: Fully safe, all edge cases handled""",
        ),
    ),
    Characteristic(
        id="minimality",
        name="Solution Minimality",
        description="Is the solution minimal without unnecessary changes?",
        prompt_template=_BASE_PROMPT.format(
            issue_title="{issue_title}",
            issue_body="{issue_body}",
            diff="{diff}",
            task_description="""Evaluate the MINIMALITY of this solution.
- Does the solution make only necessary changes?
- Is there any unnecessary code or over-engineering?
- Are there unrelated changes that shouldn't be included?

Score 1-10 where:
- 1-3: Many unnecessary changes, over-engineered
- 4-6: Some unnecessary additions
- 7-9: Mostly minimal with few extras
- 10: Perfectly minimal, only necessary changes""",
        ),
    ),
]


def get_characteristic(characteristic_id: str) -> Characteristic:
    """Get a characteristic by ID.

    Args:
        characteristic_id: The characteristic ID (e.g., "correctness").

    Returns:
        The Characteristic object.

    Raises:
        ValueError: If the characteristic ID is not found.
    """
    for c in CHARACTERISTICS:
        if c.id == characteristic_id:
            return c
    raise ValueError(f"Unknown characteristic: {characteristic_id}")
