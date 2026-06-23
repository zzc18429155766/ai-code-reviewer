"""Output formatters for review results."""

from __future__ import annotations

import json
from typing import TextIO
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .models import FileReview, ReviewIssue, ReviewResult, Severity


def format_text(result: ReviewResult, console: Console | None = None) -> str:
    """Format review results as rich terminal output."""
    if console is None:
        console = Console(record=True, width=100)

    # Header
    score_color = _score_color(result.overall_score)
    header = Text()
    header.append("🤖 AI Code Review", style="bold")
    header.append(f"\n\nOverall Score: ", style="dim")
    header.append(f"{result.overall_score}/100", style=f"bold {score_color}")

    if result.total_issues > 0:
        critical = sum(1 for i in result.all_issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in result.all_issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in result.all_issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in result.all_issues if i.severity == Severity.LOW)
        info = sum(1 for i in result.all_issues if i.severity == Severity.INFO)

        header.append(f"\n\n🔴 Critical: {critical}  🟠 High: {high}  🟡 Medium: {medium}  🔵 Low: {low}  ⚪ Info: {info}", style="dim")

    console.print(Panel(header, border_style=score_color, expand=False))

    # Per-file results
    for file_review in result.files:
        _print_file_review(file_review, console)

    # Summary
    if result.summary:
        console.print(Panel(result.summary, title="📋 Summary", border_style="blue"))

    return console.export_text()


def format_json(result: ReviewResult) -> str:
    """Format review results as JSON."""
    return json.dumps(result.to_dict(), indent=2)


def format_markdown(result: ReviewResult) -> str:
    """Format review results as GitHub-flavored Markdown."""
    lines = []

    score_emoji = "✅" if result.overall_score >= 80 else "⚠️" if result.overall_score >= 60 else "❌"
    lines.append(f"## {score_emoji} AI Code Review — Score: {result.overall_score}/100\n")

    # Summary table
    if result.total_issues > 0:
        critical = sum(1 for i in result.all_issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in result.all_issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in result.all_issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in result.all_issues if i.severity == Severity.LOW)

        lines.append("| 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low |")
        lines.append("|:-----------:|:-------:|:---------:|:------:|")
        lines.append(f"| {critical} | {high} | {medium} | {low} |")
        lines.append("")

    # Per-file details
    for file_review in result.files:
        if not file_review.issues and file_review.score >= 90:
            lines.append(f"### ✅ `{file_review.file}` — Score: {file_review.score}/100")
            lines.append(f"> {file_review.summary}\n")
            continue

        file_emoji = "❌" if file_review.score < 60 else "⚠️" if file_review.score < 80 else "✅"
        lines.append(f"### {file_emoji} `{file_review.file}` — Score: {file_review.score}/100\n")

        if file_review.summary:
            lines.append(f"> {file_review.summary}\n")

        for issue in file_review.issues:
            severity_icon = issue.severity.emoji
            category_icon = issue.category.emoji
            line_ref = f" (line {issue.line})" if issue.line else ""

            lines.append(f"#### {severity_icon} {category_icon} {issue.title}{line_ref}")
            lines.append(f"**Severity:** {issue.severity.value.upper()} | **Category:** {issue.category.value}\n")
            lines.append(issue.description)

            if issue.suggestion:
                lines.append(f"\n<details><summary>💡 Suggested fix</summary>\n")
                lines.append(f"```\n{issue.suggestion}\n```\n</details>\n")

    # Footer
    lines.append("---")
    lines.append("*Reviewed by [AI Code Reviewer](https://github.com/zzc18429155766/ai-code-reviewer)*")

    return "\n".join(lines)


def _print_file_review(file_review: FileReview, console: Console) -> None:
    """Print a single file's review."""
    score_color = _score_color(file_review.score)
    file_emoji = "❌" if file_review.score < 60 else "⚠️" if file_review.score < 80 else "✅"

    header = Text()
    header.append(f"{file_emoji} {file_review.file}", style="bold")
    header.append(f"  Score: {file_review.score}/100", style=score_color)

    if file_review.summary:
        header.append(f"\n{file_review.summary}", style="dim")

    if not file_review.issues:
        console.print(Panel(header, border_style="green", expand=False))
        return

    console.print(Panel(header, border_style=score_color, expand=False))

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Severity", width=10)
    table.add_column("Category", width=14)
    table.add_column("Line", width=6, justify="right")
    table.add_column("Issue", min_width=40)

    for issue in file_review.issues:
        line_str = str(issue.line) if issue.line else "—"
        issue_text = Text()
        issue_text.append(issue.title, style="bold")
        if issue.description:
            issue_text.append(f"\n{issue.description}", style="dim")
        if issue.suggestion:
            issue_text.append(f"\n💡 ", style="green")
            issue_text.append(issue.suggestion, style="green dim")

        table.add_row(
            f"{issue.severity.emoji} {issue.severity.value}",
            f"{issue.category.emoji} {issue.category.value}",
            line_str,
            issue_text,
        )

    console.print(table)
    console.print()


def _score_color(score: int) -> str:
    """Get color name for a score."""
    if score >= 90:
        return "green"
    elif score >= 70:
        return "yellow"
    elif score >= 50:
        return "dark_orange"
    return "red"


FORMATTERS = {
    "text": format_text,
    "json": format_json,
    "markdown": format_markdown,
}
