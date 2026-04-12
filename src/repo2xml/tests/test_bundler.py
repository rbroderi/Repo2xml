"""Functional tests for repo2xml bundler."""

from __future__ import annotations

import tempfile
from pathlib import Path

from repo2xml._bundler import RepoBundler
from repo2xml._bundler import bundle_repo


def test_bundle_produces_valid_xml() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "hello.py").write_text("print('hello')\n", encoding="utf-8")
        (repo / "README.md").write_text("# Hello\n", encoding="utf-8")

        result = RepoBundler(repo).bundle()

        assert result.startswith("<?xml")
        assert "<repository>" in result
        assert "hello.py" in result
        assert "README.md" in result
        assert "print('hello')" in result


def test_bundle_respects_gitignore() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
        (repo / "public.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "secret.txt").write_text("password=123\n", encoding="utf-8")

        files = RepoBundler(repo, respect_gitignore=True).collect_files()

        names = [f.name for f in files]
        assert "public.py" in names
        assert "secret.txt" not in names


def test_no_gitignore_flag_includes_ignored_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
        (repo / "secret.txt").write_text("data\n", encoding="utf-8")

        files = RepoBundler(repo, respect_gitignore=False).collect_files()

        names = [f.name for f in files]
        assert "secret.txt" in names


def test_extra_ignore_patterns() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "include.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "exclude.log").write_text("log data\n", encoding="utf-8")

        files = RepoBundler(repo, extra_ignore_patterns=["*.log"]).collect_files()

        names = [f.name for f in files]
        assert "include.py" in names
        assert "exclude.log" not in names


def test_max_file_size_excludes_large_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "small.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "large.txt").write_bytes(b"A" * 100)

        files = RepoBundler(repo, max_file_size=50).collect_files()

        names = [f.name for f in files]
        assert "small.py" in names
        assert "large.txt" not in names


def test_binary_files_excluded() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "script.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "data.bin").write_bytes(b"\x00\x01\x02\x03binary data")

        files = RepoBundler(repo).collect_files()

        names = [f.name for f in files]
        assert "script.py" in names
        assert "data.bin" not in names


def test_nested_directory_tree() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("", encoding="utf-8")
        (repo / "README.md").write_text("", encoding="utf-8")

        bundler = RepoBundler(repo)
        files = bundler.collect_files()
        tree = bundler.build_file_tree(files)

        assert "src/" in tree
        assert "main.py" in tree
        assert "README.md" in tree


def test_bundle_repo_convenience_function() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "app.py").write_text("x = 42\n", encoding="utf-8")

        xml = bundle_repo(repo)

        assert "<repository>" in xml
        assert "app.py" in xml


def test_bundle_repo_writes_output_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "app.py").write_text("x = 42\n", encoding="utf-8")
        out_file = Path(tmpdir) / "output.xml"

        bundle_repo(repo, output_path=out_file)

        assert out_file.exists()
        assert "<repository>" in out_file.read_text(encoding="utf-8")


def test_always_excluded_dirs_skipped() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "__pycache__").mkdir()
        (repo / "__pycache__" / "module.pyc").write_bytes(b"bytecode")
        (repo / "app.py").write_text("x = 1\n", encoding="utf-8")

        files = RepoBundler(repo).collect_files()

        paths_str = [str(f.relative_to(repo)) for f in files]
        assert all("__pycache__" not in p for p in paths_str)
        assert any("app.py" in p for p in paths_str)
