# repo2xml

Bundle a complete repository into a single XML file that ChatGPT or other LLMs can read — inspired by [repomix](https://github.com/yamadashy/repomix).

## Features

- Walks any directory tree and collects all text files
- Respects `.gitignore` rules (via [pathspec](https://github.com/cpburnz/python-pathspec))
- Skips binary files and common build/cache directories automatically
- Outputs a well-formed XML document with a directory tree and full file contents
- CLI tool (`repo2xml`) and importable Python API

## Installation

```bash
pip install repo2xml
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install repo2xml
```

## Usage

### CLI

```bash
# Bundle current directory to stdout
repo2xml

# Bundle a specific directory and save to a file
repo2xml /path/to/repo -o repo.xml

# Skip .gitignore and add extra exclusions
repo2xml --no-gitignore --ignore "*.log" --ignore "tests/"
```

### Python API

```python
from repo2xml import bundle_repo, RepoBundler

# Simple one-liner
xml = bundle_repo("/path/to/repo")

# More control
bundler = RepoBundler(
    repo_path,
    respect_gitignore=True,
    max_file_size=500_000,
    extra_ignore_patterns=["*.csv", "data/"],
)
xml = bundler.bundle()
```

## Output Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<repository>
  <file_summary>
    <purpose>...</purpose>
    <usage_guidelines>...</usage_guidelines>
  </file_summary>
  <repository_info>
    <name>my-repo</name>
    <path>/home/user/my-repo</path>
    <file_count>42</file_count>
  </repository_info>
  <directory_structure>
    my-repo/
    ├── README.md
    └── src/
        └── main.py
  </directory_structure>
  <files>
    <file path="README.md">
      <content>...</content>
    </file>
  </files>
</repository>
```

## Development

Requires [uv](https://github.com/astral-sh/uv).

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest --doctest-modules

# Lint and format
uvx ruff check src
uvx ruff format src
```
