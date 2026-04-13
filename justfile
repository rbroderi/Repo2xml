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
    uv sync --extra docs --extra dev
    just sphinx-build
    uv run zensical build --clean

# Serve documentation locally with live reload
docs-serve:
    uv sync --extra docs --extra dev
    just sphinx-build
    uv run zensical serve

# Generate and build API docs with Sphinx
sphinx-build:
    if (Test-Path docs_sphinx/apidoc) { Remove-Item -Recurse -Force docs_sphinx/apidoc }
    if (Test-Path docs_sphinx/generated) { Remove-Item -Recurse -Force docs_sphinx/generated }
    if (Test-Path docs/api) { Remove-Item -Recurse -Force docs/api }
    $env:SPHINX_APIDOC_OPTIONS = "show-inheritance"
    uv run sphinx-apidoc -f --remove-old -o docs_sphinx/apidoc src/repo2xml src/repo2xml/tests
    Get-ChildItem docs_sphinx/apidoc/*.rst | ForEach-Object { (Get-Content $_.FullName) | Where-Object { $_ -notmatch '^\s+:members:$' -and $_ -notmatch '^\s+:undoc-members:$' } | Set-Content $_.FullName }
    uv run sphinx-build -b html docs_sphinx docs/api

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
