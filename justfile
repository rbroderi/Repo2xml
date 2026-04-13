set shell := ["powershell", "-NoProfile", "-Command"]

_default:
    @just --list

# Lint and format check
ruff:
    uvx ruff check --exclude typings src
    uvx ruff format --exclude typings src

# Run Python type checking with basedpyright
typecheck:
    uvx basedpyright

# Run tests
test:
    uv run pytest --doctest-modules

# Run tests with coverage report
test-cov:
    uv run pytest --doctest-modules --cov=src/repo2xml --cov-report=term-missing

# Build documentation site with Zensical
docs-build:
    uv sync --extra docs
    uv run zensical build --clean

# Serve documentation locally with live reload
docs-serve:
    uv sync --extra docs
    uv run zensical serve

# Audit dependencies for known vulnerabilities
pip-audit:
    uv run pip-audit .

# Build standalone executable with PyInstaller
build:
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
    uv run pyinstaller build.spec

import '.justfiles/prek.just'
import '.justfiles/github_actions.just'
import '.justfiles/license.just'
