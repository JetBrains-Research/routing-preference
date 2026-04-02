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
    id: str                         # e.g., "flask__flask-5234"
    repo: str                       # e.g., "pallets/flask"
    number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
    state: str = "open"             # open/closed
    created_at: str = ""
    updated_at: str = ""
    author: str = ""
    author_association: str = ""    # MEMBER, CONTRIBUTOR, NONE, etc.
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

    # Reviewer assignment
    assigned_reviewer: str | None = None
    reviewer_type: str | None = None   # maintainer/author

    # Metadata
    collected_at: str = ""
    collection_version: str = "1.0"

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now().isoformat()

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


@dataclass
class Reviewer:
    """A maintainer who can review solutions."""

    github_username: str
    repos: list[str] = field(default_factory=list)
    email: str | None = None
    consent_given: bool = False
    max_reviews: int = 10
    assigned_issues: list[str] = field(default_factory=list)

    @property
    def available_capacity(self) -> int:
        """Number of additional reviews this reviewer can accept."""
        return max(0, self.max_reviews - len(self.assigned_issues))


@dataclass
class Repository:
    """A GitHub repository to collect issues from."""

    owner: str
    name: str
    stars: int = 0
    language: str = ""
    open_issues_count: int = 0
    last_commit_date: str | None = None
    is_active: bool = True
    maintainers: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @classmethod
    def from_github_repo(cls, repo: dict) -> "Repository":
        """Create a Repository from GitHub API response."""
        return cls(
            owner=repo["owner"]["login"],
            name=repo["name"],
            stars=repo.get("stargazers_count", 0),
            language=repo.get("language") or "",
            open_issues_count=repo.get("open_issues_count", 0),
        )
