"""Core review engine using OpenAI-compatible API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import ReviewConfig, SEVERITY_ORDER
from .languages import detect_language
from .models import Category, FileReview, ReviewIssue, ReviewResult, Severity
from .prompts import SYSTEM_PROMPT, build_review_prompt


class CodeReviewer:
    """AI-powered code reviewer."""

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key or "dummy",
            base_url=config.api_base,
        )

    def review_code(self, code: str, filename: str, language: str | None = None) -> FileReview:
        """Review a single code snippet."""
        if not language:
            language = detect_language(filename) or "unknown"

        prompt = build_review_prompt(
            code=code,
            filename=filename,
            language=language,
            categories=self.config.categories,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
        except Exception as e:
            return FileReview(
                file=filename,
                language=language,
                summary=f"API error: {e}",
                score=0,
            )

        return self._parse_response(content, filename, language)

    def review_file(self, filepath: str | Path) -> FileReview:
        """Review a single file."""
        path = Path(filepath)
        code = path.read_text(errors="replace")

        if len(code) > self.config.max_file_size:
            return FileReview(
                file=str(path),
                language="unknown",
                summary=f"File too large ({len(code)} bytes, max {self.config.max_file_size})",
                score=100,
            )

        language = detect_language(str(path))
        return self.review_code(code, str(path), language)

    def review_files(self, filepaths: list[str | Path]) -> ReviewResult:
        """Review multiple files and produce a combined result."""
        result = ReviewResult()

        for filepath in filepaths[:self.config.max_files]:
            file_review = self.review_file(filepath)
            result.files.append(file_review)

        # Calculate overall stats
        all_issues = result.all_issues
        result.total_issues = len(all_issues)

        if result.files:
            result.overall_score = sum(f.score for f in result.files) // len(result.files)
        else:
            result.overall_score = 100

        # Filter by severity threshold
        threshold = SEVERITY_ORDER.get(self.config.severity_threshold, 0)
        for file_review in result.files:
            file_review.issues = [
                i for i in file_review.issues
                if SEVERITY_ORDER.get(i.severity.value, 0) >= threshold
            ]

        return result

    def review_diff(self, diff: str, filename: str) -> FileReview:
        """Review a git diff."""
        changed_lines = self._extract_changed_lines(diff)
        if not changed_lines:
            return FileReview(file=filename, language="unknown", summary="No changes to review", score=100)

        language = detect_language(filename) or "unknown"
        return self.review_code(diff, filename, language)

    def _parse_response(self, content: str, filename: str, language: str) -> FileReview:
        """Parse the AI response into a FileReview."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fences
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    return FileReview(
                        file=filename,
                        language=language,
                        summary="Failed to parse AI response",
                        score=50,
                    )
            else:
                return FileReview(
                    file=filename,
                    language=language,
                    summary="Failed to parse AI response",
                    score=50,
                )

        issues = []
        for issue_data in data.get("issues", []):
            try:
                severity = Severity(issue_data.get("severity", "info"))
            except ValueError:
                severity = Severity.INFO

            try:
                category = Category(issue_data.get("category", "quality"))
            except ValueError:
                category = Category.QUALITY

            issues.append(ReviewIssue(
                file=filename,
                line=issue_data.get("line"),
                severity=severity,
                category=category,
                title=issue_data.get("title", "Unknown issue"),
                description=issue_data.get("description", ""),
                suggestion=issue_data.get("suggestion"),
            ))

        return FileReview(
            file=filename,
            language=language,
            issues=issues,
            summary=data.get("summary", ""),
            score=min(100, max(0, data.get("score", 50))),
        )

    @staticmethod
    def _extract_changed_lines(diff: str) -> list[str]:
        """Extract added/changed lines from a unified diff."""
        lines = []
        for line in diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])
        return lines
