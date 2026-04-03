"""Filtering logic for collected issues."""

import logging
import re
from dataclasses import dataclass, field
from typing import Callable

from .models import CollectedIssue

logger = logging.getLogger(__name__)

# Common bot patterns
BOT_PATTERNS = [
    r"\[bot\]$",
    r"-bot$",
    r"^dependabot",
    r"^renovate",
    r"^github-actions",
    r"^codecov",
    r"^snyk",
    r"^greenkeeper",
    r"^imgbot",
    r"^allcontributors",
]

# AI-generated content patterns
AI_PATTERNS = [
    r"I'd be happy to",
    r"I'll help you",
    r"Certainly!",
    r"I can help",
    r"Here's a",
    r"Let me",
    r"I understand",
    r"That's a great question",
    r"I apologize",
    r"As an AI",
]

# Duplicate label patterns
DUPLICATE_LABELS = [
    "duplicate",
    "duplicated",
    "dupe",
    "wontfix",
    "won't fix",
    "invalid",
    "not a bug",
    "by design",
]

# Low-quality title patterns
LOW_QUALITY_TITLES = [
    r"^bug$",
    r"^help$",
    r"^issue$",
    r"^problem$",
    r"^error$",
    r"^question$",
    r"^\?+$",
    r"^test$",
]


@dataclass
class FilterResult:
    """Result of applying a filter."""

    passed: bool
    reason: str = ""


@dataclass
class FilterStats:
    """Statistics about filtering."""

    total_processed: int = 0
    total_passed: int = 0
    filter_counts: dict[str, int] = field(default_factory=dict)

    def record_rejection(self, filter_name: str) -> None:
        """Record that an issue was rejected by a specific filter."""
        self.filter_counts[filter_name] = self.filter_counts.get(filter_name, 0) + 1

    def summary(self) -> str:
        lines = [
            f"Processed: {self.total_processed}",
            f"Passed: {self.total_passed} ({100 * self.total_passed / max(1, self.total_processed):.1f}%)",
            "Filtered out by:",
        ]
        for name, count in sorted(self.filter_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count}")
        return "\n".join(lines)


class IssueFilter:
    """Applies filtering criteria to issues."""

    def __init__(
        self,
        min_body_length: int = 100,
        require_engagement: bool = True,
        check_ai_content: bool = True,
        check_language: bool = True,
    ):
        """Initialize the filter.

        Args:
            min_body_length: Minimum characters in issue body.
            require_engagement: Require at least 1 reaction or comment.
            check_ai_content: Flag potential AI-generated content.
            check_language: Check for English language.
        """
        self.min_body_length = min_body_length
        self.require_engagement = require_engagement
        self.check_ai_content = check_ai_content
        self.check_language = check_language
        self.stats = FilterStats()

        # Build filter chain
        self._filters: list[tuple[str, Callable[[CollectedIssue], FilterResult]]] = [
            ("has_body", self._filter_has_body),
            ("not_bot", self._filter_not_bot),
            ("not_duplicate", self._filter_not_duplicate),
            ("quality_title", self._filter_quality_title),
        ]

        if require_engagement:
            self._filters.append(("has_engagement", self._filter_has_engagement))

        if check_ai_content:
            self._filters.append(("not_ai_generated", self._filter_not_ai_generated))

        if check_language:
            self._filters.append(("is_english", self._filter_is_english))

    def filter(self, issue: CollectedIssue) -> tuple[bool, str]:
        """Apply all filters to an issue.

        Args:
            issue: The issue to filter.

        Returns:
            Tuple of (passed, reason). If passed is True, reason is empty.
        """
        self.stats.total_processed += 1

        for filter_name, filter_func in self._filters:
            result = filter_func(issue)
            if not result.passed:
                self.stats.record_rejection(filter_name)
                return False, result.reason

        self.stats.total_passed += 1
        return True, ""

    def filter_batch(
        self,
        issues: list[CollectedIssue],
    ) -> tuple[list[CollectedIssue], list[tuple[CollectedIssue, str]]]:
        """Filter a batch of issues.

        Args:
            issues: List of issues to filter.

        Returns:
            Tuple of (passed_issues, rejected_with_reasons).
        """
        passed = []
        rejected = []

        for issue in issues:
            ok, reason = self.filter(issue)
            if ok:
                passed.append(issue)
            else:
                rejected.append((issue, reason))

        return passed, rejected

    def _filter_has_body(self, issue: CollectedIssue) -> FilterResult:
        """Check that issue has a meaningful body."""
        if not issue.body:
            return FilterResult(False, "Empty body")
        if len(issue.body.strip()) < self.min_body_length:
            return FilterResult(False, f"Body too short ({len(issue.body)} chars)")
        return FilterResult(True)

    def _filter_not_bot(self, issue: CollectedIssue) -> FilterResult:
        """Check that issue was not created by a bot."""
        author = issue.author.lower()
        for pattern in BOT_PATTERNS:
            if re.search(pattern, author, re.IGNORECASE):
                return FilterResult(False, f"Bot author: {issue.author}")
        return FilterResult(True)

    def _filter_not_duplicate(self, issue: CollectedIssue) -> FilterResult:
        """Check that issue is not marked as duplicate."""
        labels_lower = [label.lower() for label in issue.labels]
        for dup_label in DUPLICATE_LABELS:
            if dup_label in labels_lower:
                return FilterResult(False, f"Duplicate label: {dup_label}")
        return FilterResult(True)

    def _filter_quality_title(self, issue: CollectedIssue) -> FilterResult:
        """Check that issue has a descriptive title."""
        title = issue.title.strip().lower()
        for pattern in LOW_QUALITY_TITLES:
            if re.match(pattern, title, re.IGNORECASE):
                return FilterResult(False, f"Low-quality title: {issue.title}")
        if len(issue.title.strip()) < 10:
            return FilterResult(False, f"Title too short: {issue.title}")
        return FilterResult(True)

    def _filter_has_engagement(self, issue: CollectedIssue) -> FilterResult:
        """Check that issue has at least some community engagement."""
        if issue.reactions_count > 0 or issue.comments_count > 0:
            return FilterResult(True)
        return FilterResult(False, "No engagement (0 reactions, 0 comments)")

    def _filter_not_ai_generated(self, issue: CollectedIssue) -> FilterResult:
        """Check for patterns that suggest AI-generated content."""
        text = f"{issue.title} {issue.body}"
        matches = []
        for pattern in AI_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)

        # Flag if multiple AI patterns found
        if len(matches) >= 2:
            return FilterResult(False, f"Possible AI content: {matches[:3]}")
        return FilterResult(True)

    def _filter_is_english(self, issue: CollectedIssue) -> FilterResult:
        """Check that issue is in English."""
        try:
            from langdetect import detect, LangDetectException
        except ImportError:
            logger.warning("langdetect not installed, skipping language check")
            return FilterResult(True)

        text = f"{issue.title} {issue.body}"
        if len(text) < 50:
            # Too short to reliably detect
            return FilterResult(True)

        try:
            lang = detect(text)
            if lang == "en":
                issue.language_confidence = 1.0
                return FilterResult(True)
            else:
                issue.language_confidence = 0.0
                return FilterResult(False, f"Non-English language detected: {lang}")
        except LangDetectException:
            # Can't determine language, assume English
            return FilterResult(True)

    def get_stats(self) -> FilterStats:
        """Get filtering statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset filtering statistics."""
        self.stats = FilterStats()
