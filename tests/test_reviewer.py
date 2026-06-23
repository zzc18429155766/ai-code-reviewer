"""Tests for AI Code Reviewer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_code_reviewer.config import ReviewConfig
from ai_code_reviewer.languages import SUPPORTED_LANGUAGES, detect_language, get_language_display
from ai_code_reviewer.models import (
    Category,
    FileReview,
    ReviewIssue,
    ReviewResult,
    Severity,
)
from ai_code_reviewer.scanner import filter_changed_files, scan_directory
from ai_code_reviewer.formatters import format_json, format_markdown
from ai_code_reviewer.prompts import SYSTEM_PROMPT, build_review_prompt


# ──────────────────────────────────────────────
# Language Detection
# ──────────────────────────────────────────────

class TestLanguageDetection:
    def test_python(self):
        assert detect_language("main.py") == "python"
        assert detect_language("types.pyi") == "python"
        assert detect_language("app.pyw") == "python"

    def test_javascript(self):
        assert detect_language("app.js") == "javascript"
        assert detect_language("component.jsx") == "javascript"
        assert detect_language("module.mjs") == "javascript"

    def test_typescript(self):
        assert detect_language("index.ts") == "typescript"
        assert detect_language("App.tsx") == "typescript"

    def test_go(self):
        assert detect_language("main.go") == "go"

    def test_rust(self):
        assert detect_language("lib.rs") == "rust"

    def test_java(self):
        assert detect_language("Main.java") == "java"

    def test_c_cpp(self):
        assert detect_language("main.c") == "c"
        assert detect_language("main.cpp") == "cpp"
        assert detect_language("header.hpp") == "cpp"

    def test_csharp(self):
        assert detect_language("Program.cs") == "csharp"

    def test_ruby(self):
        assert detect_language("app.rb") == "ruby"

    def test_php(self):
        assert detect_language("index.php") == "php"

    def test_swift(self):
        assert detect_language("Main.swift") == "swift"

    def test_kotlin(self):
        assert detect_language("App.kt") == "kotlin"

    def test_shell(self):
        assert detect_language("run.sh") == "shell"
        assert detect_language("setup.bash") == "shell"

    def test_sql(self):
        assert detect_language("query.sql") == "sql"

    def test_yaml(self):
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("config.yml") == "yaml"

    def test_dart(self):
        assert detect_language("main.dart") == "dart"

    def test_terraform(self):
        assert detect_language("main.tf") == "terraform"

    def test_dockerfile(self):
        assert detect_language("Dockerfile") == "dockerfile"

    def test_unknown(self):
        assert detect_language("file.xyz") is None
        assert detect_language("README") is None

    def test_nested_path(self):
        assert detect_language("src/utils/helper.py") == "python"
        assert detect_language("lib/components/Button.tsx") == "typescript"

    def test_supported_languages_count(self):
        assert len(SUPPORTED_LANGUAGES) >= 15

    def test_get_language_display(self):
        assert get_language_display("python") == "Python"
        assert get_language_display("csharp") == "C#"
        assert get_language_display("unknown_lang") == "Unknown_Lang"


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class TestModels:
    def test_severity_emoji(self):
        assert Severity.CRITICAL.emoji == "🔴"
        assert Severity.HIGH.emoji == "🟠"
        assert Severity.MEDIUM.emoji == "🟡"
        assert Severity.LOW.emoji == "🔵"
        assert Severity.INFO.emoji == "⚪"

    def test_severity_ordering(self):
        assert Severity.CRITICAL.numeric > Severity.HIGH.numeric
        assert Severity.HIGH.numeric > Severity.MEDIUM.numeric
        assert Severity.MEDIUM.numeric > Severity.LOW.numeric
        assert Severity.LOW.numeric > Severity.INFO.numeric

    def test_category_emoji(self):
        assert Category.SECURITY.emoji == "🛡️"
        assert Category.PERFORMANCE.emoji == "⚡"
        assert Category.BUG.emoji == "🐛"

    def test_review_issue_to_dict(self):
        issue = ReviewIssue(
            file="test.py",
            line=42,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="SQL Injection",
            description="Unsafe query",
            suggestion="Use parameterized queries",
        )
        d = issue.to_dict()
        assert d["file"] == "test.py"
        assert d["line"] == 42
        assert d["severity"] == "high"
        assert d["category"] == "security"

    def test_file_review_counts(self):
        fr = FileReview(
            file="test.py",
            language="python",
            issues=[
                ReviewIssue("test.py", 1, Severity.CRITICAL, Category.SECURITY, "c", "d"),
                ReviewIssue("test.py", 2, Severity.HIGH, Category.BUG, "h", "d"),
                ReviewIssue("test.py", 3, Severity.MEDIUM, Category.STYLE, "m", "d"),
                ReviewIssue("test.py", 4, Severity.LOW, Category.QUALITY, "l", "d"),
            ],
        )
        assert fr.critical_count == 1
        assert fr.high_count == 1
        assert fr.medium_count == 1
        assert fr.low_count == 1

    def test_review_result_aggregation(self):
        result = ReviewResult(
            files=[
                FileReview("a.py", "python", score=80),
                FileReview("b.py", "python", score=90),
            ],
        )
        result.total_issues = 0
        result.overall_score = sum(f.score for f in result.files) // len(result.files)
        assert result.overall_score == 85

    def test_file_review_to_dict(self):
        fr = FileReview(
            file="test.py",
            language="python",
            summary="Looks good",
            score=95,
            issues=[],
        )
        d = fr.to_dict()
        assert d["score"] == 95
        assert d["language"] == "python"
        assert d["issue_counts"]["critical"] == 0


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

class TestConfig:
    def test_default_config(self):
        cfg = ReviewConfig()
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.1
        assert cfg.max_tokens == 4096
        assert cfg.output_format == "text"
        assert len(cfg.categories) == 6

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("AI_REVIEWER_MODEL", "gpt-3.5-turbo")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

        cfg = ReviewConfig.from_env()
        assert cfg.api_key == "test-key-123"
        assert cfg.model == "gpt-3.5-turbo"
        assert cfg.repo == "owner/repo"

    def test_config_from_file(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
model: gpt-4
temperature: 0.5
categories:
  - security
  - performance
ignore_patterns:
  - "*.test.js"
""")
        cfg = ReviewConfig.from_file(config_file)
        assert cfg.model == "gpt-4"
        assert cfg.temperature == 0.5
        assert cfg.categories == ["security", "performance"]

    def test_config_from_nonexistent_file(self):
        cfg = ReviewConfig.from_file("/nonexistent/path.yml")
        assert cfg.model == "gpt-4o"  # defaults preserved


# ──────────────────────────────────────────────
# Scanner
# ──────────────────────────────────────────────

class TestScanner:
    def test_scan_directory(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "app.js").write_text("console.log('hello')")
        (tmp_path / "data.json").write_text("{}")  # json has empty comment, should still be detected
        (tmp_path / "image.png").write_bytes(b"\x89PNG")

        found = scan_directory(tmp_path)
        names = [f.name for f in found]
        assert "main.py" in names
        assert "app.js" in names
        assert "image.png" not in names

    def test_scan_with_ignore(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "test_min.js").write_text("var x=1")

        # Create a min.js file
        (tmp_path / "bundle.min.js").write_text("var x=1")

        found = scan_directory(tmp_path, ignore_patterns=["*.min.js"])
        names = [f.name for f in found]
        assert "main.py" in names
        assert "bundle.min.js" not in names

    def test_scan_subdirectories(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("x = 1")

        lib = src / "lib"
        lib.mkdir()
        (lib / "utils.py").write_text("y = 2")

        found = scan_directory(tmp_path)
        assert len(found) == 2

    def test_filter_changed_files(self):
        files = [
            "src/main.py",
            "README.md",
            "lib/utils.ts",
            "data.json",
            "image.png",
            "node_modules/pkg/index.js",
        ]
        result = filter_changed_files(files, ignore_patterns=["node_modules/*"])
        assert "src/main.py" in result
        assert "lib/utils.ts" in result
        assert "README.md" not in result
        assert "image.png" not in result
        assert "node_modules/pkg/index.js" not in result


# ──────────────────────────────────────────────
# Formatters
# ──────────────────────────────────────────────

class TestFormatters:
    def _make_result(self) -> ReviewResult:
        return ReviewResult(
            files=[
                FileReview(
                    file="app.py",
                    language="python",
                    score=75,
                    summary="Some issues found",
                    issues=[
                        ReviewIssue(
                            file="app.py",
                            line=10,
                            severity=Severity.HIGH,
                            category=Category.SECURITY,
                            title="SQL Injection Risk",
                            description="User input used directly in query",
                            suggestion="Use parameterized queries",
                        ),
                        ReviewIssue(
                            file="app.py",
                            line=25,
                            severity=Severity.LOW,
                            category=Category.STYLE,
                            title="Missing type hint",
                            description="Function missing return type hint",
                        ),
                    ],
                ),
                FileReview(
                    file="utils.js",
                    language="javascript",
                    score=95,
                    summary="Clean code",
                    issues=[],
                ),
            ],
            total_issues=2,
            overall_score=85,
            summary="Good overall quality with some security concerns",
        )

    def test_json_format(self):
        result = self._make_result()
        output = format_json(result)
        data = json.loads(output)

        assert data["overall_score"] == 85
        assert data["total_issues"] == 2
        assert len(data["files"]) == 2
        assert data["files"][0]["file"] == "app.py"
        assert data["files"][0]["issues"][0]["severity"] == "high"

    def test_markdown_format(self):
        result = self._make_result()
        output = format_markdown(result)

        assert "AI Code Review" in output
        assert "85/100" in output
        assert "app.py" in output
        assert "SQL Injection Risk" in output
        assert "parameterized queries" in output

    def test_markdown_clean_file(self):
        result = self._make_result()
        output = format_markdown(result)
        assert "✅" in output  # should show green check for clean file

    def test_json_round_trip(self):
        result = self._make_result()
        output = format_json(result)
        data = json.loads(output)
        # Should be valid JSON with all expected fields
        assert "overall_score" in data
        assert "files" in data
        assert "total_issues" in data


# ──────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────

class TestPrompts:
    def test_system_prompt_exists(self):
        assert len(SYSTEM_PROMPT) > 50
        assert "JSON" in SYSTEM_PROMPT

    def test_build_review_prompt(self):
        prompt = build_review_prompt(
            code="def foo(): pass",
            filename="test.py",
            language="python",
            categories=["quality", "security"],
        )
        assert "python" in prompt
        assert "test.py" in prompt
        assert "def foo(): pass" in prompt
        assert "quality" in prompt.lower()
        assert "security" in prompt.lower()
        assert "JSON" in prompt

    def test_review_prompt_includes_all_categories(self):
        prompt = build_review_prompt(
            code="x = 1",
            filename="test.py",
            language="python",
            categories=["quality", "security", "performance", "style", "bug", "maintainability"],
        )
        assert "quality" in prompt.lower()
        assert "security" in prompt.lower()
        assert "performance" in prompt.lower()
        assert "style" in prompt.lower()
        assert "bug" in prompt.lower()
        assert "maintainability" in prompt.lower()


# ──────────────────────────────────────────────
# Reviewer (with mocked API)
# ──────────────────────────────────────────────

class TestReviewer:
    def _mock_response(self, content: dict) -> MagicMock:
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(content)
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    def test_review_code_success(self):
        from ai_code_reviewer.reviewer import CodeReviewer

        config = ReviewConfig(api_key="test-key")
        reviewer = CodeReviewer(config)

        mock_data = {
            "score": 85,
            "summary": "Good code with minor issues",
            "issues": [
                {
                    "line": 5,
                    "severity": "medium",
                    "category": "style",
                    "title": "Missing docstring",
                    "description": "Function lacks documentation",
                    "suggestion": "Add a docstring",
                }
            ],
        }

        with patch.object(reviewer.client.chat.completions, "create") as mock_create:
            mock_create.return_value = self._mock_response(mock_data)
            result = reviewer.review_code("def foo(): pass", "test.py", "python")

        assert result.score == 85
        assert result.language == "python"
        assert len(result.issues) == 1
        assert result.issues[0].title == "Missing docstring"
        assert result.issues[0].severity == Severity.MEDIUM

    def test_review_code_handles_invalid_json(self):
        from ai_code_reviewer.reviewer import CodeReviewer

        config = ReviewConfig(api_key="test-key")
        reviewer = CodeReviewer(config)

        mock_choice = MagicMock()
        mock_choice.message.content = "not valid json {"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        with patch.object(reviewer.client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_completion
            result = reviewer.review_code("x = 1", "test.py", "python")

        assert result.score == 50  # fallback
        assert "Failed to parse" in result.summary

    def test_review_code_handles_api_error(self):
        from ai_code_reviewer.reviewer import CodeReviewer

        config = ReviewConfig(api_key="test-key")
        reviewer = CodeReviewer(config)

        with patch.object(reviewer.client.chat.completions, "create") as mock_create:
            mock_create.side_effect = Exception("API Error: rate limited")
            result = reviewer.review_code("x = 1", "test.py", "python")

        assert result.score == 0
        assert "API error" in result.summary

    def test_review_files(self):
        from ai_code_reviewer.reviewer import CodeReviewer

        config = ReviewConfig(api_key="test-key")
        reviewer = CodeReviewer(config)

        mock_data = {
            "score": 90,
            "summary": "Clean code",
            "issues": [],
        }

        with patch.object(reviewer.client.chat.completions, "create") as mock_create:
            mock_create.return_value = self._mock_response(mock_data)

            result = reviewer.review_files([
                Path("test1.py"),
                Path("test2.py"),
            ])

        assert len(result.files) == 2
        assert result.overall_score == 90

    def test_review_code_with_markdown_fenced_json(self):
        from ai_code_reviewer.reviewer import CodeReviewer

        config = ReviewConfig(api_key="test-key")
        reviewer = CodeReviewer(config)

        mock_choice = MagicMock()
        mock_choice.message.content = '```json\n{"score": 80, "summary": "ok", "issues": []}\n```'
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        with patch.object(reviewer.client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_completion
            result = reviewer.review_code("x = 1", "test.py", "python")

        assert result.score == 80


# ──────────────────────────────────────────────
# Integration: parse sample AI response
# ──────────────────────────────────────────────

class TestIntegration:
    def test_full_parse_pipeline(self):
        from ai_code_reviewer.reviewer import CodeReviewer

        sample_response = json.dumps({
            "score": 72,
            "summary": "Code has some security concerns and style issues",
            "issues": [
                {
                    "line": 15,
                    "severity": "high",
                    "category": "security",
                    "title": "Hardcoded credentials",
                    "description": "API key is hardcoded in source",
                    "suggestion": "Use environment variables: os.environ['API_KEY']",
                },
                {
                    "line": 28,
                    "severity": "medium",
                    "category": "performance",
                    "title": "N+1 query pattern",
                    "description": "Database query inside a loop",
                    "suggestion": "Use bulk query with IN clause",
                },
                {
                    "line": None,
                    "severity": "low",
                    "category": "style",
                    "title": "Inconsistent naming",
                    "description": "Mix of camelCase and snake_case",
                },
            ],
        })

        config = ReviewConfig(api_key="test-key")
        reviewer = CodeReviewer(config)
        result = reviewer._parse_response(sample_response, "app.py", "python")

        assert result.score == 72
        assert len(result.issues) == 3
        assert result.issues[0].severity == Severity.HIGH
        assert result.issues[0].category == Category.SECURITY
        assert result.issues[1].severity == Severity.MEDIUM
        assert result.issues[2].line is None

        # Test full formatter pipeline
        review_result = ReviewResult(
            files=[result],
            total_issues=3,
            overall_score=72,
        )

        json_output = format_json(review_result)
        data = json.loads(json_output)
        assert data["overall_score"] == 72

        md_output = format_markdown(review_result)
        assert "Hardcoded credentials" in md_output
        assert "N+1 query" in md_output
