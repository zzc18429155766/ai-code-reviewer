"""GitHub Action integration — posts review comments on PRs."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from .config import ReviewConfig
from .formatters import format_markdown
from .models import ReviewResult


class GitHubIntegration:
    """Handles GitHub PR comment posting."""

    API_BASE = "https://api.github.com"

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.headers = {
            "Authorization": f"token {config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ai-code-reviewer",
        }

    def get_pr_files(self) -> list[dict]:
        """Fetch the list of files changed in a PR."""
        url = f"{self.API_BASE}/repos/{self.config.repo}/pulls/{self.config.pr_number}/files"
        resp = httpx.get(url, headers=self.headers, params={"per_page": 100})
        resp.raise_for_status()
        return resp.json()

    def get_pr_diff(self) -> str:
        """Fetch the full PR diff."""
        url = f"{self.API_BASE}/repos/{self.config.repo}/pulls/{self.config.pr_number}"
        resp = httpx.get(url, headers=self.headers, headers2={"Accept": "application/vnd.github.v3.diff"})
        # Alternative: use the diff directly
        resp = httpx.get(url, headers={**self.headers, "Accept": "application/vnd.github.v3.diff"})
        resp.raise_for_status()
        return resp.text

    def post_comment(self, body: str) -> dict:
        """Post a comment on the PR."""
        url = f"{self.API_BASE}/repos/{self.config.repo}/issues/{self.config.pr_number}/comments"
        resp = httpx.post(url, headers=self.headers, json={"body": body})
        resp.raise_for_status()
        return resp.json()

    def update_comment(self, comment_id: int, body: str) -> dict:
        """Update an existing comment."""
        url = f"{self.API_BASE}/repos/{self.config.repo}/issues/comments/{comment_id}"
        resp = httpx.patch(url, headers=self.headers, json={"body": body})
        resp.raise_for_status()
        return resp.json()

    def find_existing_comment(self) -> int | None:
        """Find an existing review comment from this bot."""
        url = f"{self.API_BASE}/repos/{self.config.repo}/issues/{self.config.pr_number}/comments"
        resp = httpx.get(url, headers=self.headers, params={"per_page": 100})
        resp.raise_for_status()

        for comment in resp.json():
            if "AI Code Review" in comment.get("body", ""):
                return comment["id"]
        return None

    def post_review(self, result: ReviewResult) -> None:
        """Post or update the review comment on the PR."""
        body = format_markdown(result)
        existing_id = self.find_existing_comment()

        if existing_id:
            self.update_comment(existing_id, body)
        else:
            self.post_comment(body)

    def set_output(self, result: ReviewResult) -> None:
        """Set GitHub Action outputs."""
        output_file = os.environ.get("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"score={result.overall_score}\n")
                f.write(f"issues={result.total_issues}\n")
                f.write(f"critical={sum(1 for i in result.all_issues if i.severity.value == 'critical')}\n")

    def should_fail(self, result: ReviewResult) -> bool:
        """Check if the review should fail the workflow."""
        if self.config.fail_on_critical:
            if any(i.severity.value == "critical" for i in result.all_issues):
                return True
        if result.overall_score < self.config.fail_threshold:
            return True
        return False


def get_changed_files_from_event() -> list[str]:
    """Get changed files from GitHub event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return []

    import json
    with open(event_path) as f:
        event = json.load(f)

    return [
        f["filename"]
        for f in event.get("pull_request", {}).get("changed_files_data", [])
    ]
