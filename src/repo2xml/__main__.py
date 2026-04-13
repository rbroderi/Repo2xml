"""Command-line interface for repo2xml."""

import argparse
import sys
from pathlib import Path

from repo2xml.bundler import BundleReadError
from repo2xml.bundler import DefaultExclude
from repo2xml.bundler import RepoBundler
from repo2xml.bundler import get_version

OK = 0
ERROR = 1


def _print_excluded_paths(extra_patterns: list[str], include_patterns: list[str]) -> None:
    excluded_dirs = ", ".join(value.value for value in DefaultExclude)
    extra = ", ".join(extra_patterns) if extra_patterns else "(none)"
    include = ", ".join(include_patterns) if include_patterns else "(none)"
    print(f"Excluding directories/files: {excluded_dirs}", file=sys.stderr)
    print(f"Extra exclude patterns: {extra}", file=sys.stderr)
    print(f"Include override patterns: {include}", file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo2xml",
        description="Bundle a repository into a single XML file for LLMs.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show program version and exit",
    )
    parser.add_argument(
        "-p",
        "--repo-path",
        help="Path to the repository to bundle",
        required=True,
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
    parser.add_argument(
        "-i",
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Pattern to include even if default or extra excludes match (repeatable)",
    )
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show progress bar during bundling (default: auto-detect interactive terminal)",
    )
    return parser


def main() -> int:
    """Entry point for the repo2xml CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.is_dir():
        print(f"error: {repo_path} is not a directory", file=sys.stderr)
        return ERROR

    if sys.stderr.isatty() or sys.stdout.isatty():
        _print_excluded_paths(args.ignore, args.include)

    bundler = RepoBundler(
        repo_path,
        respect_gitignore=not args.no_gitignore,
        max_file_size=args.max_file_size,
        extra_ignore_patterns=args.ignore,
        include_patterns=args.include,
    )
    if args.progress is None:
        show_progress = sys.stderr.isatty() or sys.stdout.isatty()
    else:
        show_progress = args.progress
    try:
        xml_content = bundler.bundle(show_progress=show_progress)
    except BundleReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return ERROR

    if args.output:
        Path(args.output).write_text(xml_content, encoding="utf-8")
    else:
        if sys.stdout.isatty():
            print(xml_content)
        else:
            # Redirected output should always be UTF-8 encoded bytes.
            sys.stdout.buffer.write(xml_content.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
    return OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
