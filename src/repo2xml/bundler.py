"""Core repository bundling logic."""

import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import cast

import pathspec
from identify.identify import tags_from_path
from magika import Magika
from markitdown import MarkItDown
from puremagic import PureError
from puremagic import from_file as puremagic_from_file

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

_TEXT_ENCODINGS: tuple[str, ...] = (
    "utf-8",
    "utf-8-sig",
    "cp1252",
    "latin-1",
)

_TEXT_APPLICATION_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/json",
        "application/xml",
        "application/ecmascript",
        "application/javascript",
        "application/x-javascript",
        "application/rtf",
        "application/x-rtf",
        "application/x-tex",
        "application/x-texinfo",
        "application/x-latex",
        "application/x-tcl",
        "application/x-csh",
        "application/x-ksh",
        "application/x-lisp",
        "application/x-sh",
        "application/x-shellscript",
        "application/x-wais-source",
        "application/x-yaml",
        "application/yaml",
        "application/toml",
        "application/sql",
    }
)


class BundleReadError(RuntimeError):
    """Raised when a repository file cannot be read during bundling."""


@lru_cache(maxsize=1)
def _get_magika() -> Magika:
    """Return a cached Magika instance for file type detection."""
    return Magika()


def _load_gitignore_spec(repo_path: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns from *repo_path* and return a :class:`pathspec.PathSpec`."""
    gitignore = repo_path / ".gitignore"
    if gitignore.exists():
        try:
            patterns = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            msg = f"failed to read {gitignore}: {exc}"
            raise BundleReadError(msg) from exc
    else:
        patterns = []
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _is_text_file(path: Path) -> bool:
    """Return ``True`` if *path* is likely a text file."""
    try:
        result = _get_magika().identify_path(path)
    except OSError as exc:
        msg = f"failed to read {path}: {exc}"
        raise BundleReadError(msg) from exc

    if result.status.value != "ok":
        msg = f"failed to read {path}: magika status {result.status.value}"
        raise BundleReadError(msg)

    if result.prediction.output.is_text:
        return True

    try:
        mime = puremagic_from_file(path, mime=True)
    except (PureError, OSError, ValueError):
        mime = ""
    mime = mime.lower()
    if mime.startswith("text/"):
        return True
    if mime in _TEXT_APPLICATION_MIME_TYPES:
        return True
    if mime.endswith("+json") or mime.endswith("+xml") or mime.endswith("+yaml"):
        return True

    try:
        tags = tags_from_path(str(path))
    except (OSError, ValueError):
        tags = set()

    if "text" in tags:
        return True
    if "binary" in tags:
        return False

    return False


def _read_text_file(path: Path) -> str:
    """Read *path* using UTF-8 first, then common fallback encodings."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        msg = f"failed to read {path}: {exc}"
        raise BundleReadError(msg) from exc

    # Decode UTF-16 only when BOM is present to avoid false positives on 8-bit text.
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass

    for encoding in _TEXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    msg = f"failed to decode {path} with supported encodings"
    raise BundleReadError(msg)


def _convert_file_to_markdown(path: Path, converter: MarkItDown) -> str | None:
    """Convert *path* to Markdown when supported; return ``None`` when unsupported."""
    try:
        result = converter.convert_local(str(path))
    except Exception:
        return None

    markdown = (result.markdown or result.text_content or "").strip()
    return markdown or None


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
                child: dict[str, object] = {}
                node[part] = child
                existing = child
            node = cast(dict[str, object], existing)
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
                _render(cast(dict[str, object], val), new_indent)

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
        self._repo_path: Path
        self._respect_gitignore: bool
        self._max_file_size: int
        self._repo_path = repo_path.resolve()
        self._respect_gitignore = respect_gitignore
        self._max_file_size = max_file_size
        self._extra_spec: pathspec.PathSpec = pathspec.PathSpec.from_lines("gitignore", extra_ignore_patterns or [])

    def _candidate_files(self) -> list[Path]:
        """Return candidate files after ignore and size filtering."""
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
            try:
                file_size = path.stat().st_size
            except OSError:
                continue
            if file_size == 0:
                continue
            if file_size > self._max_file_size:
                continue
            results.append(path)
        return results

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
        results: list[Path] = []
        for path in self._candidate_files():
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
        ...     _ = (p / "src" / "main.py").write_text("print('x')\\n")
        ...     _ = (p / "README.md").write_text("# Readme\\n")
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
        included_files: list[tuple[Path, str]] = []
        converter = MarkItDown()
        for file_path in self._candidate_files():
            if _is_text_file(file_path):
                content = _read_text_file(file_path)
            else:
                markdown = _convert_file_to_markdown(file_path, converter)
                if markdown is None:
                    continue
                content = markdown
            included_files.append((file_path, content))

        files = [path for path, _ in included_files]
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
        for file_path, content in included_files:
            rel = str(file_path.relative_to(self._repo_path))
            file_elem = ET.SubElement(files_elem, "file", path=rel)
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
