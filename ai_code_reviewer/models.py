"""Data models for review results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def emoji(self) -> str:
        return {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "⚪",
        }[self.value]

    @property
    def numeric(self) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[self.value]


class Category(str, Enum):
    """Review category."""
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BUG = "bug"
    MAINTAINABILITY = "maintainability"

    @property
    def emoji(self) -> str:
        return {
            "quality": "✨",
            "security": "🛡️",
            "performance": "⚡",
            "style": "🎨",
            "bug": "🐛",
            "maintainability": "🔧",
        }[self.value]


@dataclass
class ReviewIssue:
    """A single review finding."""
    file: str
    line: int | None
    severity: Severity
    category: Category
    title: str
    description: str
    suggestion: str | None = None
    code_snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
        }


@dataclass
class FileReview:
    """Review results for a single file."""
    file: str
    language: str
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    score: int = 100  # 0-100 quality score

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.LOW)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "language": self.language,
            "score": self.score,
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "issue_counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
        }


@dataclass
class ReviewResult:
    """Complete review result across all files."""
    files: list[FileReview] = field(default_factory=list)
    total_issues: int = 0
    overall_score: int = 100
    summary: str = ""

    @property
    def all_issues(self) -> list[ReviewIssue]:
        issues = []
        for f in self.files:
            issues.extend(f.issues)
        return issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "total_issues": self.total_issues,
            "summary": self.summary,
            "files": [f.to_dict() for f in self.files],
        }
