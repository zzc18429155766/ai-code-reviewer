"""AI prompt templates for code review."""

SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices, security vulnerabilities, performance optimization, and clean code principles.

Your task is to review code and provide actionable feedback. Be specific, constructive, and cite concrete examples. Focus on real issues, not nitpicks.

IMPORTANT: Respond ONLY with valid JSON. No markdown fences, no extra text."""


def build_review_prompt(
    code: str,
    filename: str,
    language: str,
    categories: list[str],
) -> str:
    """Build the user prompt for a code review."""

    category_instructions = {
        "quality": "- Code quality: complexity, readability, DRY violations, proper abstractions, error handling",
        "security": "- Security: injection risks, auth issues, secrets exposure, input validation, OWASP Top 10",
        "performance": "- Performance: N+1 queries, unnecessary allocations, missing caching, algorithmic complexity",
        "style": "- Style: naming conventions, formatting consistency, documentation, type hints/annotations",
        "bug": "- Bugs: logic errors, off-by-one, null/nil dereference, race conditions, unhandled edge cases",
        "maintainability": "- Maintainability: coupling, cohesion, test coverage implications, dependency concerns",
    }

    category_text = "\n".join(
        category_instructions[c] for c in categories if c in category_instructions
    )

    return f"""Review this {language} code from `{filename}`:

```{language}
{code}
```

Analyze these categories:
{category_text}

Return a JSON object with this exact structure:
{{
  "score": <0-100 integer, 100=perfect>,
  "summary": "<one-line summary of overall quality>",
  "issues": [
    {{
      "line": <line number or null>,
      "severity": "<critical|high|medium|low|info>",
      "category": "<one of: quality|security|performance|style|bug|maintainability>",
      "title": "<short issue title>",
      "description": "<detailed explanation>",
      "suggestion": "<specific fix with code example>"
    }}
  ]
}}

Guidelines:
- Only report real, meaningful issues
- Include line numbers when possible
- Suggest concrete fixes with code examples
- Score fairly: 90-100 excellent, 70-89 good, 50-69 needs work, below 50 serious issues
- If code is clean, say so with a high score and few or no issues
- Limit to the 10 most important issues"""


def build_pr_summary_prompt(file_reviews: list[dict]) -> str:
    """Build a prompt for generating a PR summary."""
    import json

    return f"""Based on these code review results, write a brief PR review summary.

Results:
{json.dumps(file_reviews, indent=2)}

Return a JSON object:
{{
  "overall_assessment": "<2-3 sentence summary>",
  "strengths": ["<strength1>", "<strength2>"],
  "concerns": ["<concern1>", "<concern2>"],
  "recommendation": "<approve|request_changes|comment>"
}}

Be constructive and specific."""
