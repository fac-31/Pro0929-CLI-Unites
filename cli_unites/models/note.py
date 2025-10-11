"""Dataclass encapsulating a project note."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Note:
    id: str
    title: str
    body: str
    created_at: datetime
    tags: List[str] = field(default_factory=list)
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    project_path: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "Note":
        # Handle tags - can be a comma-separated string or None
        tags_str = row.get("tags") or ""
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []

        # Handle created_at - can be a string or datetime object
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        return cls(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            created_at=created_at,
            tags=tags,
            git_commit=row.get("git_commit"),
            git_branch=row.get("git_branch"),
            project_path=row.get("project_path"),
        )

    def to_cli_output(self) -> str:
        tag_str = f" [tags: {', '.join(self.tags)}]" if self.tags else ""
        git_str = f" (commit {self.git_commit[:7]} on {self.git_branch})" if self.git_commit and self.git_branch else ""
        return f"{self.title}{tag_str}{git_str}\n{self.body}"

    def matches_tag(self, tag: str) -> bool:
        return tag in self.tags

    @property
    def summary(self) -> str:
        snippet = self.body.strip().splitlines()[0] if self.body else ""
        return f"{self.title}: {snippet[:60]}" if snippet else self.title
