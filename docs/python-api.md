# Python API

Use `bundle_repo` for the one-liner path, or `RepoBundler` for full control.

## One-liner

```python
from repo2xml import bundle_repo

xml = bundle_repo("/path/to/repo")
```

## Advanced

```python
from pathlib import Path
from repo2xml import RepoBundler

bundler = RepoBundler(
    Path("/path/to/repo"),
    respect_gitignore=True,
    max_file_size=1_000_000,
    extra_ignore_patterns=["*.log"],
    include_patterns=[".git/**"],
)
xml = bundler.bundle()
```
