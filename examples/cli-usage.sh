# Example: review a single file
ai-code-reviewer review app.py

# Review a directory
ai-code-reviewer review src/

# Review with specific model
ai-code-reviewer review . --model gpt-4o-mini

# Save JSON report
ai-code-reviewer review src/ --format json --save report.json

# Review only critical/high issues
ai-code-reviewer review . --severity high

# Initialize config file
ai-code-reviewer init
