"""Issue type and complexity classification."""

import logging
import re

import litellm

from .models import CollectedIssue, Complexity, IssueType, TypeSource

logger = logging.getLogger(__name__)

# Label patterns for issue type classification
BUG_LABELS = {
    "bug",
    "defect",
    "error",
    "crash",
    "regression",
    "fix",
    "bugfix",
    "type: bug",
    "kind: bug",
    "type/bug",
    "bug-fix",
    "confirmed bug",
}

FEATURE_LABELS = {
    "feature",
    "enhancement",
    "feature-request",
    "improvement",
    "new feature",
    "type: feature",
    "kind: feature",
    "type/feature",
    "rfe",
    "idea",
    "type: enhancement",
    "kind: enhancement",
}

# Keywords for complexity estimation
SIMPLE_KEYWORDS = {
    "typo",
    "spelling",
    "docstring",
    "comment",
    "rename",
    "type hint",
    "typing",
    "annotation",
    "deprecation warning",
    "import",
}

COMPLEX_KEYWORDS = {
    "refactor",
    "redesign",
    "rewrite",
    "architecture",
    "breaking change",
    "migration",
    "overhaul",
    "rearchitect",
    "major",
}


class IssueClassifier:
    """Classifies issues by type and complexity."""

    def __init__(self, llm_model: str = "openai/gpt-4o-mini"):
        """Initialize the classifier.

        Args:
            llm_model: Model to use for LLM-based classification.
        """
        self.llm_model = llm_model

    def classify_type_from_labels(
        self,
        issue: CollectedIssue,
    ) -> tuple[IssueType, float]:
        """Classify issue type based on labels.

        Args:
            issue: The issue to classify.

        Returns:
            Tuple of (issue_type, confidence).
        """
        labels_lower = {label.lower() for label in issue.labels}

        # Check for bug labels
        if labels_lower & BUG_LABELS:
            return IssueType.BUG, 1.0

        # Check for feature labels
        if labels_lower & FEATURE_LABELS:
            return IssueType.FEATURE, 1.0

        return IssueType.OTHER, 0.0

    def classify_type_with_llm(
        self,
        issue: CollectedIssue,
    ) -> tuple[IssueType, float]:
        """Classify issue type using LLM.

        Args:
            issue: The issue to classify.

        Returns:
            Tuple of (issue_type, confidence).
        """
        prompt = f"""Classify this GitHub issue as one of: BUG, FEATURE, or OTHER.

Title: {issue.title}

Description:
{issue.body[:2000]}

Respond with ONLY one word: BUG, FEATURE, or OTHER."""

        try:
            response = litellm.completion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )
            answer = response.choices[0].message.content.strip().upper()

            if "BUG" in answer:
                return IssueType.BUG, 0.8
            elif "FEATURE" in answer:
                return IssueType.FEATURE, 0.8
            else:
                return IssueType.OTHER, 0.8

        except Exception as e:
            logger.warning("LLM classification failed: %s", e)
            return IssueType.OTHER, 0.0

    def classify_type(
        self,
        issue: CollectedIssue,
        use_llm_fallback: bool = True,
    ) -> CollectedIssue:
        """Classify issue type and update the issue.

        Args:
            issue: The issue to classify.
            use_llm_fallback: Use LLM if labels don't indicate type.

        Returns:
            Updated issue with type classification.
        """
        # Try label-based classification first
        issue_type, confidence = self.classify_type_from_labels(issue)

        if issue_type != IssueType.OTHER:
            issue.issue_type = issue_type
            issue.issue_type_source = TypeSource.LABEL
            issue.issue_type_confidence = confidence
            return issue

        # Fall back to LLM if enabled
        if use_llm_fallback:
            issue_type, confidence = self.classify_type_with_llm(issue)
            issue.issue_type = issue_type
            issue.issue_type_source = TypeSource.LLM
            issue.issue_type_confidence = confidence
        else:
            issue.issue_type = IssueType.OTHER
            issue.issue_type_source = TypeSource.UNKNOWN
            issue.issue_type_confidence = 0.0

        return issue

    def estimate_complexity(self, issue: CollectedIssue) -> CollectedIssue:
        """Estimate issue complexity based on heuristics.

        Args:
            issue: The issue to analyze.

        Returns:
            Updated issue with complexity estimate.
        """
        text = f"{issue.title} {issue.body}".lower()

        # Check for simple keywords
        for keyword in SIMPLE_KEYWORDS:
            if keyword in text:
                issue.complexity = Complexity.SIMPLE
                return issue

        # Check for complex keywords
        for keyword in COMPLEX_KEYWORDS:
            if keyword in text:
                issue.complexity = Complexity.COMPLEX
                return issue

        # Count code blocks and file references
        code_blocks = len(re.findall(r"```", issue.body))
        file_refs = len(re.findall(r"[\w/]+\.(py|js|ts|go|rs|java)\b", issue.body))

        # Estimate based on content length and references
        body_length = len(issue.body)

        if body_length < 300 and file_refs <= 1:
            issue.complexity = Complexity.SIMPLE
        elif body_length > 1500 or file_refs >= 5 or code_blocks >= 4:
            issue.complexity = Complexity.COMPLEX
        else:
            issue.complexity = Complexity.MEDIUM

        return issue

    def classify(
        self,
        issue: CollectedIssue,
        use_llm_fallback: bool = True,
    ) -> CollectedIssue:
        """Fully classify an issue (type and complexity).

        Args:
            issue: The issue to classify.
            use_llm_fallback: Use LLM for type if labels missing.

        Returns:
            Updated issue with classifications.
        """
        issue = self.classify_type(issue, use_llm_fallback=use_llm_fallback)
        issue = self.estimate_complexity(issue)
        return issue

    def classify_batch(
        self,
        issues: list[CollectedIssue],
        use_llm_fallback: bool = True,
    ) -> list[CollectedIssue]:
        """Classify a batch of issues.

        Args:
            issues: List of issues to classify.
            use_llm_fallback: Use LLM for type if labels missing.

        Returns:
            List of classified issues.
        """
        classified = []
        for issue in issues:
            try:
                classified.append(self.classify(issue, use_llm_fallback))
            except Exception as e:
                logger.warning("Failed to classify %s: %s", issue.issue_id, e)
                classified.append(issue)
        return classified
