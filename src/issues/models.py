"""Data models for issue collection."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IssueType(str, Enum):
    """Type of GitHub issue."""

    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class Complexity(str, Enum):
    """Estimated complexity of the issue."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


class TypeSource(str, Enum):
    """How the issue type was determined."""

    LABEL = "label"
    LLM = "llm"
    UNKNOWN = "unknown"


@dataclass
class CollectedIssue:
    """A GitHub issue collected for the dataset."""

    # Core fields (from GitHub)
    id: str  # e.g., "flask__flask-5234"
    repo: str  # e.g., "pallets/flask"
    number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
    state: str = "open"  # open/closed
    created_at: str = ""
    updated_at: str = ""
    author: str = ""
    author_association: str = ""  # MEMBER, CONTRIBUTOR, NONE, etc.
    comments_count: int = 0
    reactions_count: int = 0
    html_url: str = ""

    # Derived fields
    issue_type: IssueType = IssueType.OTHER
    issue_type_source: TypeSource = TypeSource.UNKNOWN
    issue_type_confidence: float = 0.0
    complexity: Complexity = Complexity.UNKNOWN
    language_confidence: float = 1.0  # English detection score

    # For mini-swe-agent
    base_commit: str | None = None

    # Vestigial fields from the dormant reviewer-assignment flow.
    # Kept on the dataclass so existing JSON files in data/issues/ continue
    # to deserialize via CollectedIssue(**data). Always None on new collections.
    assigned_reviewer: str | None = None
    reviewer_type: str | None = None

    # Metadata
    collected_at: str = ""
    collection_version: str = "1.0"

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()

    @property
    def issue_id(self) -> str:
        """Compatibility alias used by the generation dataset schema."""
        return self.id

    @classmethod
    def from_github_issue(cls, repo: str, issue: dict) -> "CollectedIssue":
        """Create a CollectedIssue from GitHub API response."""
        number = issue["number"]
        repo_slug = repo.replace("/", "__")
        issue_id = f"{repo_slug}-{number}"

        return cls(
            id=issue_id,
            repo=repo,
            number=number,
            title=issue.get("title", ""),
            body=issue.get("body") or "",
            labels=[label["name"] for label in issue.get("labels", [])],
            state=issue.get("state", "open"),
            created_at=issue.get("created_at", ""),
            updated_at=issue.get("updated_at", ""),
            author=issue.get("user", {}).get("login", ""),
            author_association=issue.get("author_association", ""),
            comments_count=issue.get("comments", 0),
            reactions_count=issue.get("reactions", {}).get("total_count", 0),
            html_url=issue.get("html_url", ""),
        )


