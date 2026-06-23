"""Language detection and file extension mapping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    name: str
    extensions: tuple[str, ...]
    comment_style: str = "//"  # single-line comment prefix


SUPPORTED_LANGUAGES: dict[str, Language] = {
    "python": Language("Python", (".py", ".pyi", ".pyw"), "#"),
    "javascript": Language("JavaScript", (".js", ".jsx", ".mjs", ".cjs"), "//"),
    "typescript": Language("TypeScript", (".ts", ".tsx", ".mts", ".cts"), "//"),
    "java": Language("Java", (".java",), "//"),
    "go": Language("Go", (".go",), "//"),
    "rust": Language("Rust", (".rs",), "//"),
    "c": Language("C", (".c", ".h"), "//"),
    "cpp": Language("C++", (".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"), "//"),
    "csharp": Language("C#", (".cs",), "//"),
    "ruby": Language("Ruby", (".rb", ".erb"), "#"),
    "php": Language("PHP", (".php", ".phtml"), "//"),
    "swift": Language("Swift", (".swift",), "//"),
    "kotlin": Language("Kotlin", (".kt", ".kts"), "//"),
    "scala": Language("Scala", (".scala", ".sc"), "//"),
    "shell": Language("Shell", (".sh", ".bash", ".zsh", ".fish"), "#"),
    "sql": Language("SQL", (".sql",), "--"),
    "yaml": Language("YAML", (".yaml", ".yml"), "#"),
    "json": Language("JSON", (".json",), ""),
    "xml": Language("XML", (".xml", ".svg"), ""),
    "html": Language("HTML", (".html", ".htm"), ""),
    "css": Language("CSS", (".css",), ""),
    "scss": Language("SCSS", (".scss", ".sass"), "//"),
    "dart": Language("Dart", (".dart",), "//"),
    "lua": Language("Lua", (".lua",), "--"),
    "r": Language("R", (".r", ".R"), "#"),
    "perl": Language("Perl", (".pl", ".pm", ".t"), "#"),
    "elixir": Language("Elixir", (".ex", ".exs"), "#"),
    "haskell": Language("Haskell", (".hs", ".lhs"), "--"),
    "terraform": Language("Terraform", (".tf", ".tfvars"), "#"),
    "dockerfile": Language("Dockerfile", ("Dockerfile",), "#"),
}

EXTENSION_MAP: dict[str, str] = {}
for lang_key, lang in SUPPORTED_LANGUAGES.items():
    for ext in lang.extensions:
        EXTENSION_MAP[ext] = lang_key


def detect_language(filename: str) -> str | None:
    """Detect the programming language from a filename."""
    # Handle special filenames
    base = filename.rsplit("/", 1)[-1]
    if base in ("Dockerfile", "Containerfile"):
        return "dockerfile"

    for ext, lang in EXTENSION_MAP.items():
        if filename.endswith(ext):
            return lang
    return None


def get_language_display(language_key: str) -> str:
    """Get the display name for a language."""
    if lang := SUPPORTED_LANGUAGES.get(language_key):
        return lang.name
    return language_key.title()
