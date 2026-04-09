# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (including dev tools)
uv sync

# Run tests
uv run pytest

# Run a single test file or test
uv run pytest tests/path/to/test_file.py::test_name

# Run tests with coverage
uv run pytest --cov=good_start_habits

# Lint and format
uv run ruff check .
uv run ruff format .

# Auto-fix lint issues
uv run ruff check --fix .
```

## Project Structure

- `src/good_start_habits/` — main package (src layout)
- `tests/` — pytest tests
- Uses `uv` for dependency management; `uv sync` installs everything including dev deps
- `pyproject.toml` defines both runtime deps and dev group (`dev = [mkdocs, pre-commit, pytest, pytest-cov, ruff]`)
