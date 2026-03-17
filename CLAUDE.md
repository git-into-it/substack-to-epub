# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`substack-to-epub` is a Python CLI tool (Python 3.13+) that converts Substack content to EPUB format. It uses `uv` for package management and builds via `uv_build`.

## Commands

```bash
# Install dependencies and set up environment
uv sync

# Run the CLI
uv run substack-to-epub

# Run directly
uv run python -m substack_to_epub
```

## Architecture

- `src/substack_to_epub/__init__.py` — entry point; `main()` is registered as the `substack-to-epub` CLI script in `pyproject.toml`
- All source code lives under `src/substack_to_epub/`
- No dependencies yet — add them to `pyproject.toml` under `[project] dependencies`
