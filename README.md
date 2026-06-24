<![CDATA[<div align="center">

# 🤖 AI Code Reviewer

[![GitHub Stars](https://img.shields.io/github/stars/zzc18429155766/ai-code-reviewer?style=social)](https://github.com/zzc18429155766/ai-code-reviewer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Action](https://img.shields.io/badge/GitHub-Action-brightgreen.svg)](https://github.com/marketplace/actions/ai-code-reviewer)

**AI-powered code review for every pull request. Catch bugs, security vulnerabilities, and code quality issues before they hit production.**

[Features](#-features) • [Quick Start](#-quick-start) • [GitHub Action](#-github-action) • [CLI Usage](#-cli-usage) • [Supported Languages](#-supported-languages)

---

![AI Code Reviewer Demo](https://raw.githubusercontent.com/zzc18429155766/ai-code-reviewer/main/assets/demo.gif)

</div>

---

## ✨ Features

- 🔍 **Smart Code Analysis** — AI-powered review that understands context, not just patterns
- 🛡️ **Security Scanning** — Detect SQL injection, XSS, hardcoded secrets, and more
- ⚡ **Performance Insights** — Identify N+1 queries, memory leaks, and inefficient algorithms
- 🎨 **Style Suggestions** — Enforce consistent coding standards across your team
- 🌐 **15+ Languages** — Python, JavaScript, TypeScript, Go, Rust, Java, C++, and more
- 🔄 **GitHub Action** — Automatic PR reviews on every push
- 💻 **CLI Tool** — Review code locally before committing
- 📝 **Inline Comments** — Feedback posted directly on the relevant lines of code

---

## 🚀 Quick Start

### 1. Install

```bash
pip install ai-code-reviewer
```

### 2. Set your API key

```bash
export OPENAI_API_KEY="sk-..."
```

### 3. Review a file

```bash
ai-review review src/main.py
```

### 4. Review a PR (GitHub Action)

Add to `.github/workflows/review.yml`:

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: zzc18429155766/ai-code-reviewer@v1
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

---

## 🔧 GitHub Action

### Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `openai-api-key` | OpenAI API key | **required** |
| `openai-base-url` | Custom API base URL | `https://api.openai.com/v1` |
| `model` | Model to use | `gpt-4o` |
| `review-level` | `quick`, `standard`, or `thorough` | `standard` |
| `exclude-patterns` | Files to exclude (glob) | `*.md,*.txt,*.json` |
| `max-files` | Max files to review per PR | `20` |
| `language` | Review language | `en` |

### Full Example

```yaml
- uses: zzc18429155766/ai-code-reviewer@v1
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    model: 'gpt-4o'
    review-level: 'thorough'
    exclude-patterns: '*.test.*,*.spec.*'
    max-files: 30
    language: 'en'
```

### Custom API Endpoint (Ollama, Azure, etc.)

```yaml
- uses: zzc18429155766/ai-code-reviewer@v1
  with:
    openai-api-key: ${{ secrets.API_KEY }}
    openai-base-url: 'http://localhost:11434/v1'
    model: 'codellama'
```

---

## 💻 CLI Usage

```bash
# Review a single file
ai-review review src/app.py

# Review a directory
ai-review review src/ --recursive

# Review with specific level
ai-review review src/ --level thorough

# Review only changed files (git diff)
ai-review review --diff

# Output as JSON
ai-review review src/ --format json

# Review with custom model
ai-review review src/ --model gpt-4o --base-url https://api.openai.com/v1
```

### CLI Output Example

```
$ ai-review review src/auth.py

📋 Reviewing src/auth.py...
─────────────────────────────────────────────

🔴 CRITICAL [Line 23] SQL Injection vulnerability
   User input directly interpolated in SQL query.
   Use parameterized queries instead.

   Fix: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

🟡 WARNING [Line 45] Missing input validation
   Email parameter not validated before use.
   Add email format validation.

🟢 SUGGESTION [Line 12] Use constant for magic number
   Replace `86400` with `SECONDS_PER_DAY` for clarity.

─────────────────────────────────────────────
📊 Summary: 1 critical, 1 warning, 1 suggestion
```

---

## 🌐 Supported Languages

| Language | Extensions | Review Quality |
|----------|-----------|----------------|
| Python | `.py` | ⭐⭐⭐⭐⭐ |
| JavaScript | `.js`, `.jsx`, `.mjs` | ⭐⭐⭐⭐⭐ |
| TypeScript | `.ts`, `.tsx` | ⭐⭐⭐⭐⭐ |
| Go | `.go` | ⭐⭐⭐⭐⭐ |
| Rust | `.rs` | ⭐⭐⭐⭐⭐ |
| Java | `.java` | ⭐⭐⭐⭐ |
| C/C++ | `.c`, `.cpp`, `.h`, `.hpp` | ⭐⭐⭐⭐ |
| C# | `.cs` | ⭐⭐⭐⭐ |
| Ruby | `.rb` | ⭐⭐⭐⭐ |
| PHP | `.php` | ⭐⭐⭐⭐ |
| Swift | `.swift` | ⭐⭐⭐⭐ |
| Kotlin | `.kt` | ⭐⭐⭐⭐ |
| Scala | `.scala` | ⭐⭐⭐ |
| Shell | `.sh`, `.bash` | ⭐⭐⭐ |
| SQL | `.sql` | ⭐⭐⭐ |

---

## ⚙️ Configuration

Create `.ai-review.yml` in your repo root:

```yaml
# Review settings
model: gpt-4o
review_level: standard  # quick | standard | thorough
language: en

# File filtering
exclude:
  - "*.test.*"
  - "*.spec.*"
  - "vendor/**"
  - "node_modules/**"
  - "*.min.js"

# Custom rules
rules:
  security:
    enabled: true
    severity: error
  performance:
    enabled: true
    severity: warning
  style:
    enabled: true
    severity: info

# Custom prompts (append to default)
custom_prompt: |
  This project uses Django. Pay special attention to:
  - N+1 query issues with Django ORM
  - Missing select_related/prefetch_related
  - CSRF protection in views
```

---

## 🏗️ Architecture

```
ai-code-reviewer/
├── ai_code_reviewer/
│   ├── __init__.py
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration loading
│   ├── formatters.py    # Output formatting (text, json, markdown)
│   ├── languages.py     # Language detection & extensions
│   ├── models.py        # Data models
│   ├── prompts.py       # AI prompt templates
│   ├── reviewer.py      # Core review logic
│   └── scanner.py       # File scanning & filtering
├── .github/workflows/
│   └── review.yml       # GitHub Action workflow
├── action.yml           # GitHub Action definition
├── examples/
│   └── cli-usage.sh     # CLI examples
├── tests/
│   └── test_reviewer.py # Unit tests
├── pyproject.toml       # Package configuration
└── LICENSE
```

---

## 🤝 Contributing

Contributions welcome! Here's how:

1. Fork this repo
2. Create a branch: `git checkout -b feat/amazing-feature`
3. Commit: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feat/amazing-feature`
5. Open a PR

### Development Setup

```bash
git clone https://github.com/zzc18429155766/ai-code-reviewer.git
cd ai-code-reviewer
pip install -e ".[dev]"
pytest
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">

**Built with ❤️ by [zzc18429155766](https://github.com/zzc18429155766)**

⭐ Star this repo if you find it useful!

</div>
]]>
---

## 🚀 Pro Version

Looking for more features? Check out **AI Code Reviewer Pro**:

- 🧠 **Multi-AI Backend** — OpenAI, Claude, Gemini, Ollama (local)
- 📝 **50+ Premium Prompts** — Security, performance, style, complexity
- 👥 **Team Configurations** — Shared configs for your team
- 🎥 **Video Tutorials** — Step-by-step guides
- 🔄 **1 Year Updates** — New features included

**Get it now:** https://zzcwhisper4.gumroad.com/l/ai-code-reviewer-pro

