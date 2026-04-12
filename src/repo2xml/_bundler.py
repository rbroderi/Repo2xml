"""Core repository bundling logic."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pathspec


_ALWAYS_EXCLUDE: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".pyright",
        "node_modules",
        ".eggs",
        "dist",
        "build",
        "htmlcov",
    }
)


def _load_gitignore_spec(repo_path: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns from *repo_path* and return a :class:`pathspec.PathSpec`."""
    gitignore = repo_path / ".gitignore"
    if gitignore.exists():
        patterns = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    else:
        patterns = []
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _is_text_file(path: Path, max_check_bytes: int = 8192) -> bool:
    """Return ``True`` if *path* is likely a UTF-8 text file."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(max_check_bytes)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


def _build_tree_str(files: list[Path], repo_path: Path) -> str:
    """Return a text tree diagram for *files* relative to *repo_path*."""
    rel_paths = sorted(f.relative_to(repo_path) for f in files)

    # Build a nested dict: directories map to dicts, files map to None.
    tree: dict[str, object] = {}
    for rel in rel_paths:
        node: dict[str, object] = tree
        for part in rel.parts[:-1]:
            existing = node.get(part)
            if not isinstance(existing, dict):
                node[part] = {}
            node = node[part]  # type: ignore[assignment]
        node[rel.parts[-1]] = None

    lines: list[str] = [repo_path.name + "/"]

    def _render(subtree: dict[str, object], indent: str) -> None:
        entries = sorted(subtree.items())
        for idx, (name, val) in enumerate(entries):
            is_last = idx == len(entries) - 1
            branch = "└── " if is_last else "├── "
            suffix = "/" if isinstance(val, dict) else ""
            lines.append(indent + branch + name + suffix)
            if isinstance(val, dict):
                new_indent = indent + ("    " if is_last else "│   ")
                _render(val, new_indent)

    _render(tree, "")
    return "\n".join(lines)


class RepoBundler:
    """Bundle a repository directory into a single XML representation for LLMs.

    >>> import tempfile, pathlib
    >>> with tempfile.TemporaryDirectory() as d:
    ...     p = pathlib.Path(d)
    ...     _ = (p / "hello.py").write_text("x = 1\\n")
    ...     xml = RepoBundler(p).bundle()
    ...     "hello.py" in xml
    True
    """

    def __init__(
        self,
        repo_path: Path,
        *,
        respect_gitignore: bool = True,
        max_file_size: int = 1_000_000,
        extra_ignore_patterns: list[str] | None = None,
    ) -> None:
        self._repo_path = repo_path.resolve()
        self._respect_gitignore = respect_gitignore
        self._max_file_size = max_file_size
        self._extra_spec: pathspec.PathSpec = pathspec.PathSpec.from_lines("gitignore", extra_ignore_patterns or [])

    def collect_files(self) -> list[Path]:
        """Return a sorted list of text files to include in the bundle.

        >>> import tempfile, pathlib
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = pathlib.Path(d)
        ...     _ = (p / "a.py").write_text("x = 1\\n")
        ...     _ = (p / ".gitignore").write_text("secret.txt\\n")
        ...     _ = (p / "secret.txt").write_text("s\\n")
        ...     files = RepoBundler(p).collect_files()
        ...     sorted(f.name for f in files)
        ['.gitignore', 'a.py']
        """
        gitignore_spec = (
            _load_gitignore_spec(self._repo_path)
            if self._respect_gitignore
            else pathspec.PathSpec.from_lines("gitignore", [])
        )
        results: list[Path] = []
        for path in sorted(self._repo_path.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self._repo_path)
            if any(part in _ALWAYS_EXCLUDE for part in rel.parts):
                continue
            rel_str = str(rel)
            if gitignore_spec.match_file(rel_str):
                continue
            if self._extra_spec.match_file(rel_str):
                continue
            if path.stat().st_size > self._max_file_size:
                continue
            if not _is_text_file(path):
                continue
            results.append(path)
        return results

    def build_file_tree(self, files: list[Path]) -> str:
        """Return a text tree diagram for *files*.

        >>> import tempfile, pathlib
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = pathlib.Path(d)
        ...     (p / "src").mkdir()
        ...     _ = (p / "src" / "main.py").write_text("")
        ...     _ = (p / "README.md").write_text("")
        ...     bundler = RepoBundler(p)
        ...     files = bundler.collect_files()
        ...     tree = bundler.build_file_tree(files)
        ...     "src/" in tree and "main.py" in tree
        True
        """
        return _build_tree_str(files, self._repo_path)

    def bundle(self) -> str:
        """Bundle the repository and return a well-formed XML string.

        >>> import tempfile, pathlib
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = pathlib.Path(d)
        ...     _ = (p / "hi.py").write_text("print('hi')\\n")
        ...     xml = RepoBundler(p).bundle()
        ...     xml.startswith("<?xml")
        True
        """
        files = self.collect_files()
        tree_str = self.build_file_tree(files)

        root = ET.Element("repository")

        summary = ET.SubElement(root, "file_summary")
        ET.SubElement(summary, "purpose").text = (
            "This file is a merged representation of the entire codebase, "
            "combined into a single document by repo2xml for analysis by AI language models."
        )
        ET.SubElement(summary, "usage_guidelines").text = (
            "When working with this file, an AI model should:\n"
            "1. Treat the content as a read-only snapshot of the repository.\n"
            "2. Use the directory structure to understand the project layout.\n"
            "3. Reference file paths when discussing specific code."
        )

        info = ET.SubElement(root, "repository_info")
        ET.SubElement(info, "name").text = self._repo_path.name
        ET.SubElement(info, "path").text = str(self._repo_path)
        ET.SubElement(info, "file_count").text = str(len(files))

        ET.SubElement(root, "directory_structure").text = tree_str

        files_elem = ET.SubElement(root, "files")
        for file_path in files:
            rel = str(file_path.relative_to(self._repo_path))
            file_elem = ET.SubElement(files_elem, "file", path=rel)
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = ""
            ET.SubElement(file_elem, "content").text = content

        ET.indent(root, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def bundle_repo(
    repo_path: str | Path = ".",
    *,
    output_path: str | Path | None = None,
    respect_gitignore: bool = True,
    max_file_size: int = 1_000_000,
    extra_ignore_patterns: list[str] | None = None,
) -> str:
    """Bundle a repository into a single XML string.

    Convenience wrapper around :class:`RepoBundler`.

    Args:
        repo_path: Path to the repository directory (default: current directory).
        output_path: If given, also write the XML to this file.
        respect_gitignore: Whether to respect ``.gitignore`` rules.
        max_file_size: Maximum file size in bytes to include.
        extra_ignore_patterns: Additional gitignore-style patterns to exclude.

    Returns:
        The XML representation of the repository as a string.

    >>> import tempfile, pathlib
    >>> with tempfile.TemporaryDirectory() as d:
    ...     p = pathlib.Path(d)
    ...     _ = (p / "hello.py").write_text("x = 1\\n")
    ...     xml = bundle_repo(p)
    ...     "hello.py" in xml
    True
    """
    bundler = RepoBundler(
        Path(repo_path),
        respect_gitignore=respect_gitignore,
        max_file_size=max_file_size,
        extra_ignore_patterns=extra_ignore_patterns,
    )
    xml_content = bundler.bundle()
    if output_path is not None:
        Path(output_path).write_text(xml_content, encoding="utf-8")
    return xml_content
