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

import '.justfiles/clean.just'
import '.justfiles/prek.just'
import '.justfiles/github_actions.just'
import '.justfiles/license.just'
