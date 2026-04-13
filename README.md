# repo2xml

Bundle a complete repository into a single XML file that ChatGPT
or other LLMs can read, inspired by [repomix](https://github.com/yamadashy/repomix).

## Features

- Walks any directory tree and bundles readable files into XML
- Respects `.gitignore` rules (via [pathspec](https://github.com/cpburnz/python-pathspec))
- Uses layered file detection: Magika, then `puremagic` MIME, then `identify`
- Converts supported non-text files to Markdown via `markitdown`
- Skips zero-byte files, oversized files, and common build/cache directories automatically
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
repo2xml --repo-path .

# Bundle a specific directory and save to a file
repo2xml --repo-path /path/to/repo -o repo.xml

# Skip .gitignore and add extra exclusions
repo2xml --repo-path /path/to/repo --no-gitignore --ignore "*.log" --ignore "tests/"

# Control progress display explicitly
repo2xml --repo-path /path/to/repo --progress
repo2xml --repo-path /path/to/repo --no-progress
```

When running in an interactive terminal,
`repo2xml` auto-enables a progress bar.
Progress is written to stderr, so XML output stays clean
for `-o FILE` and stdout redirection.

### Python API

```python
from repo2xml import bundle_repo, RepoBundler

# Simple one-liner
xml = bundle_repo("/path/to/repo")

# More control
bundler = RepoBundler(
    "/path/to/repo",
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
just test-cov

# Lint and format
uvx ruff check src
uvx ruff format src

# Build one-file executable via PyInstaller
just build
```
