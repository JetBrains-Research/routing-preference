"""XML tag stripping utilities."""

import re


def strip_xml_tags(content: str) -> str:
    """Remove XML wrapper tags from content.

    Example:
        Input:  <NAME>ITEXT</NAME>
        Output: TEXT
    """
    pattern = r"<[A-Z_]+>(.*?)</[A-Z_]+>"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()
