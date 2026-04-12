"""CLI tests for repo2xml."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from repo2xml import __main__ as cli
from repo2xml.bundler import BundleReadError
from repo2xml.bundler import RepoBundler


def test_main_prints_xml_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "hello.py").write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["repo2xml", "--repo-path", str(tmp_path)])
    result = cli.main()

    captured = capsys.readouterr()
    assert result == cli.OK
    assert "<?xml" in captured.out
    assert "hello.py" in captured.out


def test_main_writes_output_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    out_file = tmp_path / "bundle.xml"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "repo2xml",
            "--repo-path",
            str(tmp_path),
            "--no-gitignore",
            "--max-file-size",
            "1000",
            "--ignore",
            "*.tmp",
            "-o",
            str(out_file),
        ],
    )
    result = cli.main()

    assert result == cli.OK
    assert out_file.exists()
    assert "<repository>" in out_file.read_text(encoding="utf-8")


def test_main_returns_error_for_non_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    not_a_dir = tmp_path / "missing"

    monkeypatch.setattr(sys, "argv", ["repo2xml", "--repo-path", str(not_a_dir)])
    result = cli.main()

    captured = capsys.readouterr()
    assert result == cli.ERROR
    assert "is not a directory" in captured.err


def test_main_returns_error_for_bundle_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "hello.py").write_text("print('hello')\n", encoding="utf-8")

    def _raise_bundle_read_error(self: RepoBundler) -> str:
        del self
        raise BundleReadError("failed to read file.txt: boom")

    monkeypatch.setattr(RepoBundler, "bundle", _raise_bundle_read_error)
    monkeypatch.setattr(sys, "argv", ["repo2xml", "--repo-path", str(tmp_path)])

    result = cli.main()

    captured = capsys.readouterr()
    assert result == cli.ERROR
    assert "failed to read file.txt: boom" in captured.err


def test_module_main_guard_executes_main(tmp_path: Path) -> None:
    (tmp_path / "entry.py").write_text("x = 1\n", encoding="utf-8")
    out_file = tmp_path / "via-module.xml"

    result = subprocess.run(
        [sys.executable, "-m", "repo2xml", "-p", str(tmp_path), "-o", str(out_file)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    assert out_file.exists()
    assert "entry.py" in out_file.read_text(encoding="utf-8")
