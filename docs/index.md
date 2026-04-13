# repo2xml

Bundle a complete repository into a single XML file that LLMs can consume.

## Install

```bash
pip install repo2xml
```

Or with uv:

```bash
uv tool install repo2xml
```

## CLI quick start

```bash
# Bundle current directory to stdout
repo2xml --repo-path .

# Write XML to file
repo2xml --repo-path /path/to/repo -o repo.xml
```

## Key options

- `--ignore PATTERN`: Add extra exclude patterns.
- `--include PATTERN`: Override default and extra excludes.
- `--no-gitignore`: Disable `.gitignore` filtering.
- `--progress` / `--no-progress`: Control progress display.
