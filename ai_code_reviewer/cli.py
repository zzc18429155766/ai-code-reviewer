"""CLI interface for AI Code Reviewer."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .config import ReviewConfig
from .formatters import FORMATTERS
from .reviewer import CodeReviewer
from .scanner import scan_directory


console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="ai-code-reviewer")
def main():
    """🤖 AI Code Reviewer — AI-powered code review for humans and CI."""
    pass


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--config", "-c", type=click.Path(), default=None, help="Config file path")
@click.option("--model", "-m", default=None, help="AI model to use")
@click.option("--format", "-f", "output_format", type=click.Choice(["text", "json", "markdown"]), default=None, help="Output format")
@click.option("--severity", "-s", type=click.Choice(["info", "low", "medium", "high", "critical"]), default=None, help="Minimum severity to report")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.option("--save", type=click.Path(), default=None, help="Save output to file")
def review(paths, config, model, output_format, severity, no_color, save):
    """Review code files or directories.

    Examples:

        ai-code-reviewer review src/

        ai-code-reviewer review app.py utils.py --model gpt-4o

        ai-code-reviewer review . --format json --save report.json

        ai-code-reviewer review src/ --severity medium
    """
    cfg = ReviewConfig.load(config)

    if model:
        cfg.model = model
    if output_format:
        cfg.output_format = output_format
    if severity:
        cfg.severity_threshold = severity
    if no_color:
        cfg.color = False

    if not cfg.api_key:
        console.print("[red]Error:[/red] No API key found. Set OPENAI_API_KEY or AI_REVIEWER_API_KEY.")
        sys.exit(1)

    # Collect files to review
    files_to_review = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            files_to_review.append(path)
        elif path.is_dir():
            found = scan_directory(path, cfg.ignore_patterns)
            files_to_review.extend(found)
        else:
            console.print(f"[yellow]Warning:[/yellow] Skipping {path_str} (not found)")

    if not files_to_review:
        console.print("[yellow]No reviewable files found.[/yellow]")
        sys.exit(0)

    console.print(f"[dim]Reviewing {len(files_to_review)} file(s) with {cfg.model}...[/dim]\n")

    reviewer = CodeReviewer(cfg)
    result = reviewer.review_files(files_to_review)

    # Format and output
    fmt_func = FORMATTERS.get(cfg.output_format, FORMATTERS["text"])

    if cfg.output_format == "json":
        output = fmt_func(result)
    elif cfg.output_format == "markdown":
        output = fmt_func(result)
    else:
        output = fmt_func(result, console=console)

    if save:
        Path(save).write_text(output if isinstance(output, str) else "")
        console.print(f"\n[green]✅ Report saved to {save}[/green]")

    # Exit with error if score is below threshold
    if result.overall_score < cfg.fail_threshold:
        console.print(f"\n[red]❌ Score {result.overall_score} is below threshold {cfg.fail_threshold}[/red]")
        sys.exit(1)


@main.command()
@click.option("--config", "-c", type=click.Path(), default=None, help="Config file path")
@click.option("--model", "-m", default=None, help="AI model to use")
@click.option("--format", "-f", "output_format", type=click.Choice(["text", "json", "markdown"]), default="markdown", help="Output format")
@click.option("--post/--no-post", default=True, help="Post comment to PR")
def pr(config, model, output_format, post):
    """Review the current PR (for GitHub Actions).

    Automatically detects PR context from environment variables.
    """
    cfg = ReviewConfig.load(config)

    if model:
        cfg.model = model
    cfg.output_format = output_format

    if not cfg.api_key:
        console.print("[red]Error:[/red] No API key found. Set OPENAI_API_KEY or AI_REVIEWER_API_KEY.")
        sys.exit(1)

    if not cfg.github_token or not cfg.repo:
        console.print("[red]Error:[/red] Not running in GitHub Actions context.")
        sys.exit(1)

    from .github_action import GitHubIntegration

    gh = GitHubIntegration(cfg)

    # Get PR files
    console.print(f"[dim]Fetching PR #{cfg.pr_number} files...[/dim]")
    pr_files = gh.get_pr_files()

    changed_files = [
        f["filename"]
        for f in pr_files
        if f.get("status") != "removed"
    ]

    if not changed_files:
        console.print("[yellow]No changed files to review.[/yellow]")
        sys.exit(0)

    # Filter to reviewable files
    from .scanner import filter_changed_files
    reviewable = filter_changed_files(changed_files, cfg.ignore_patterns)

    if not reviewable:
        console.print("[yellow]No reviewable files in this PR.[/yellow]")
        sys.exit(0)

    console.print(f"[dim]Reviewing {len(reviewable)} file(s) with {cfg.model}...[/dim]\n")

    # Fetch file contents and review
    reviewer = CodeReviewer(cfg)
    file_reviews = []

    for pr_file in pr_files:
        if pr_file["filename"] not in reviewable:
            continue

        # Use patch (diff) for review
        patch = pr_file.get("patch", "")
        if not patch:
            continue

        file_review = reviewer.review_diff(patch, pr_file["filename"])
        file_reviews.append(file_review)

    from .models import ReviewResult
    result = ReviewResult(files=file_reviews)
    result.total_issues = len(result.all_issues)
    if result.files:
        result.overall_score = sum(f.score for f in result.files) // len(result.files)

    # Output
    fmt_func = FORMATTERS.get(output_format, FORMATTERS["markdown"])
    output = fmt_func(result)

    if cfg.output_format == "text":
        fmt_func(result, console=console)

    # Post to PR
    if post:
        console.print("[dim]Posting review comment...[/dim]")
        gh.post_review(result)
        gh.set_output(result)
        console.print("[green]✅ Review posted to PR[/green]")

    if gh.should_fail(result):
        console.print(f"[red]❌ Review score {result.overall_score} below threshold[/red]")
        sys.exit(1)


@main.command()
def init():
    """Create a sample .ai-reviewer.yml config file."""
    sample = """# AI Code Reviewer Configuration
# See: https://github.com/zzc18429155766/ai-code-reviewer

# AI Model settings
model: gpt-4o          # Any OpenAI-compatible model
temperature: 0.1       # Lower = more consistent reviews
max_tokens: 4096

# Review categories to enable
categories:
  - quality
  - security
  - performance
  - style
  - bug
  - maintainability

# Minimum severity to report (info, low, medium, high, critical)
severity_threshold: low

# File patterns to ignore
ignore_patterns:
  - "*.min.js"
  - "*.min.css"
  - "*.lock"
  - "node_modules/*"
  - ".git/*"
  - "__pycache__/*"
  - "*.pyc"
  - ".venv/*"
  - "dist/*"
  - "build/*"

# Output settings
output_format: text    # text, json, or markdown
show_suggestions: true

# GitHub Action settings (usually set via env vars)
# fail_on_critical: false
# fail_threshold: 50
"""
    config_path = Path(".ai-reviewer.yml")
    if config_path.exists():
        console.print("[yellow].ai-reviewer.yml already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    config_path.write_text(sample)
    console.print("[green]✅ Created .ai-reviewer.yml[/green]")


if __name__ == "__main__":
    main()
