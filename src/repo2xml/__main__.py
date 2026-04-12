"""Command-line interface for repo2xml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from repo2xml._bundler import RepoBundler


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo2xml",
        description="Bundle a repository into a single XML file for LLMs.",
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to the repository to bundle (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not respect .gitignore rules",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=1_000_000,
        metavar="BYTES",
        help="Maximum file size to include in bytes (default: 1000000)",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Extra gitignore-style pattern to exclude (repeatable)",
    )
    return parser


def main() -> None:
    """Entry point for the repo2xml CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.is_dir():
        print(f"error: {repo_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    bundler = RepoBundler(
        repo_path,
        respect_gitignore=not args.no_gitignore,
        max_file_size=args.max_file_size,
        extra_ignore_patterns=args.ignore,
    )
    xml_content = bundler.bundle()

    if args.output:
        Path(args.output).write_text(xml_content, encoding="utf-8")
    else:
        print(xml_content)


if __name__ == "__main__":
    main()
