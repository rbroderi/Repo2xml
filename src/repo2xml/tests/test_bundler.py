"""Functional tests for repo2xml bundler."""

import tempfile
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import cast

import pytest

from repo2xml.bundler import BundleReadError
from repo2xml.bundler import RepoBundler
from repo2xml.bundler import _is_text_file  # pyright: ignore[reportPrivateUsage]
from repo2xml.bundler import _read_text_file  # pyright: ignore[reportPrivateUsage]
from repo2xml.bundler import bundle_repo


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


def test_bundle_reads_non_utf8_text_file(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        # cp1252-encoded text exercises fallback decoding.
        (repo / "notes.txt").write_bytes(b"\x63\x61\x66\xe9")

        def _always_text(_path: Path) -> bool:
            return True

        monkeypatch.setattr("repo2xml.bundler._is_text_file", _always_text)

        result = RepoBundler(repo).bundle()

        assert "notes.txt" in result
        assert "café" in result


def test_bundle_includes_markitdown_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "diagram.bin").write_bytes(b"binary")

        def _always_non_text(_path: Path) -> bool:
            return False

        def _fake_convert_local(self: object, file_path: str) -> Any:
            del self
            if file_path.endswith("diagram.bin"):
                return SimpleNamespace(
                    markdown="# Converted\n\nfrom binary",
                    text_content="# Converted\n\nfrom binary",
                )
            return SimpleNamespace(markdown="", text_content="")

        monkeypatch.setattr("repo2xml.bundler._is_text_file", _always_non_text)
        monkeypatch.setattr("repo2xml.bundler.MarkItDown.convert_local", _fake_convert_local)

        result = RepoBundler(repo).bundle()

        assert "diagram.bin" in result
        assert "# Converted" in result


def test_bundle_skips_markitdown_unsupported_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "unknown.bin").write_bytes(b"binary")

        def _always_non_text(_path: Path) -> bool:
            return False

        def _failing_convert_local(self: object, file_path: str) -> Any:
            del self
            del file_path
            raise RuntimeError("unsupported")

        monkeypatch.setattr("repo2xml.bundler._is_text_file", _always_non_text)
        monkeypatch.setattr("repo2xml.bundler.MarkItDown.convert_local", _failing_convert_local)

        result = RepoBundler(repo).bundle()

        assert "unknown.bin" not in result


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


def test_zero_byte_files_are_excluded() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "empty.txt").write_text("", encoding="utf-8")
        (repo / "nonempty.txt").write_text("x\n", encoding="utf-8")

        files = RepoBundler(repo).collect_files()

        names = [f.name for f in files]
        assert "empty.txt" not in names
        assert "nonempty.txt" in names


def test_binary_files_excluded() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "script.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "data.bin").write_bytes(b"\x00\x01\x02\x03binary data")

        files = RepoBundler(repo).collect_files()

        names = [f.name for f in files]
        assert "script.py" in names
        assert "data.bin" not in names


def test_is_text_file_uses_magika_text_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.txt"
        path.write_text("hello\n", encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=True)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        assert _is_text_file(path) is True


def test_is_text_file_uses_magika_binary_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.bin"
        path.write_bytes(b"\x00")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        assert _is_text_file(path) is False


def test_is_text_file_uses_mime_fallback_when_magika_non_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.txt"
        path.write_text("", encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        def _puremagic_text(_path: Path, mime: bool = True) -> str:
            del mime
            return "text/plain"

        monkeypatch.setattr("repo2xml.bundler.puremagic_from_file", _puremagic_text)

        assert _is_text_file(path) is True


def test_is_text_file_uses_application_mime_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.json"
        path.write_text('{"x": 1}\n', encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        def _puremagic_json(_path: Path, mime: bool = True) -> str:
            del mime
            return "application/json"

        monkeypatch.setattr("repo2xml.bundler.puremagic_from_file", _puremagic_json)

        assert _is_text_file(path) is True


def test_is_text_file_uses_structured_suffix_mime_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.custom"
        path.write_text('{"x": 1}\n', encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        def _puremagic_structured(_path: Path, mime: bool = True) -> str:
            del mime
            return "application/ld+json"

        monkeypatch.setattr("repo2xml.bundler.puremagic_from_file", _puremagic_structured)

        assert _is_text_file(path) is True


def test_is_text_file_uses_identify_binary_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.bin"
        path.write_bytes(b"\x00")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        def _puremagic_binary(_path: Path, mime: bool = True) -> str:
            del mime
            return "application/octet-stream"

        def _identify_binary(_path: str) -> set[str]:
            return {"binary"}

        monkeypatch.setattr("repo2xml.bundler.puremagic_from_file", _puremagic_binary)
        monkeypatch.setattr("repo2xml.bundler.tags_from_path", _identify_binary)

        assert _is_text_file(path) is False


def test_is_text_file_returns_false_after_identify_error_without_text_mime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.py"
        path.write_text("x = 1\n", encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        def _puremagic_binary(_path: Path, mime: bool = True) -> str:
            del mime
            return "application/octet-stream"

        monkeypatch.setattr("repo2xml.bundler.puremagic_from_file", _puremagic_binary)

        def _raise_identify_error(_p: str) -> set[str]:
            raise ValueError("simulated identify error")

        monkeypatch.setattr("repo2xml.bundler.tags_from_path", _raise_identify_error)

        assert _is_text_file(path) is False


def test_is_text_file_uses_identify_after_puremagic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.unknown"
        path.write_text("hello\n", encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    status=SimpleNamespace(value="ok"),
                    prediction=SimpleNamespace(output=SimpleNamespace(is_text=False)),
                )

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        def _raise_oserror(_p: Path, mime: bool = True) -> str:
            del mime
            raise OSError("simulated puremagic read error")

        monkeypatch.setattr("repo2xml.bundler.puremagic_from_file", _raise_oserror)

        def _identify_text(_path: str) -> set[str]:
            return {"text"}

        monkeypatch.setattr("repo2xml.bundler.tags_from_path", _identify_text)

        assert _is_text_file(path) is True


def test_is_text_file_raises_for_non_ok_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "missing.txt"
        path.write_text("x\n", encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                return SimpleNamespace(status=SimpleNamespace(value="file_not_found_error"))

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        with pytest.raises(BundleReadError, match="magika status file_not_found_error"):
            _is_text_file(path)


def test_nested_directory_tree() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("print('x')\n", encoding="utf-8")
        (repo / "README.md").write_text("# Readme\n", encoding="utf-8")

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


def test_is_text_file_raises_for_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sample.txt"
        path.write_text("hello\n", encoding="utf-8")

        class _FakeMagika:
            def identify_path(self, _path: Path) -> SimpleNamespace:
                raise OSError("simulated read failure")

        monkeypatch.setattr("repo2xml.bundler._get_magika", lambda: _FakeMagika())

        with pytest.raises(BundleReadError, match="failed to read"):
            _is_text_file(path)


def test_bundle_raises_on_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        target = repo / "app.py"
        target.write_text("print('x')\n", encoding="utf-8")

        original_read_bytes = cast(Callable[..., bytes], Path.read_bytes)

        def _patched_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
            if self == target:
                raise OSError("simulated read failure")
            return original_read_bytes(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_bytes", _patched_read_bytes)

        with pytest.raises(BundleReadError, match="failed to read"):
            RepoBundler(repo).bundle()


def test_read_text_file_raises_when_all_decoders_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "bad.txt"
        target.write_bytes(b"\xff\xfe\xff")

        monkeypatch.setattr("repo2xml.bundler._TEXT_ENCODINGS", ())

        with pytest.raises(BundleReadError, match="failed to decode"):
            _read_text_file(target)


def test_collect_files_raises_for_unreadable_gitignore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        gitignore = repo / ".gitignore"
        public_file = repo / "public.py"
        secret_file = repo / "secret.txt"

        gitignore.write_text("secret.txt\n", encoding="utf-8")
        public_file.write_text("x = 1\n", encoding="utf-8")
        secret_file.write_text("secret\n", encoding="utf-8")

        original_read_text = cast(Callable[..., str], Path.read_text)

        def _patched_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
            if self == gitignore:
                raise OSError("simulated gitignore read failure")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", _patched_read_text)

        with pytest.raises(BundleReadError, match="failed to read"):
            RepoBundler(repo, respect_gitignore=True).collect_files()


def test_collect_files_skips_file_when_stat_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        bad_file = repo / "bad.py"
        good_file = repo / "good.py"

        bad_file.write_text("x = 1\n", encoding="utf-8")
        good_file.write_text("y = 2\n", encoding="utf-8")

        original_stat = Path.stat
        stat_calls: dict[Path, int] = {}

        def _patched_stat(self: Path, *args: Any, **kwargs: Any) -> Any:
            if self == bad_file:
                call_count = stat_calls.get(self, 0) + 1
                stat_calls[self] = call_count
                if call_count >= 2:
                    raise OSError("simulated stat failure")
            return original_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", _patched_stat)

        files = RepoBundler(repo).collect_files()

        names = [f.name for f in files]
        assert "good.py" in names
        assert "bad.py" not in names
