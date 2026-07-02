"""Single-pass placeholder substitution for prompt templates."""

import re


def fill_template(template: str, values: dict[str, str]) -> str:
    """Replace every placeholder in one pass over the template.

    Substituted content is never re-scanned, so issue bodies, diffs, or
    source files that happen to contain a placeholder token stay literal.
    """
    if not values:
        return template
    pattern = re.compile("|".join(re.escape(key) for key in values))
    return pattern.sub(lambda match: values[match.group(0)], template)
