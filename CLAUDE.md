# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Git Flow Action is a GitHub Action (Docker-based Python app) that automates semantic versioning and release management following Git Flow branching principles. It determines version bumps from commit messages, creates git tags, manages CHANGELOG.md, creates release branches, and publishes GitHub releases.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# Run all tests
pytest

# Run unit tests with coverage
pytest tests/unit/ -v --cov=src

# Run functional tests
pytest tests/functional/ -v

# Run a single test file
pytest tests/unit/test_changelog.py -v

# Run a single test by name
pytest tests/unit/test_changelog.py::test_function_name -v

# Generate coverage report
pytest --cov=src --cov-report=xml

# Build Docker image
docker build -t git-flow-action:latest .
```

## Architecture

All core logic lives in a single file: `src/main.py` (~750 lines). There are no submodules or abstraction layers — functions are organized by concern within that file.

### Main execution flow

```
Environment variables (GitHub Action inputs)
    → get_config()           # builds config dict
    → main()
        → git repo setup     # configure user, fetch tags
        → get_bump_type()    # parse commit message for feat/fix/BREAKING CHANGE
        → get_new_semver_version()
        → update_changelog() # optional, writes to CHANGELOG.md
        → git_create_and_push_tag()
        → create_release_branch()  # main branch only
        → create_github_release()  # via GitHub API (requests)
        → actions_output()   # set GitHub Actions output vars
```

### Branch strategy logic

- **main**: Creates release candidates (`rc/`) or full releases. If commit has `[RELEASE]` tag or `auto_release_branches=true`, also creates a `release/X.Y` branch.
- **release/X.Y**: Patch-only bumps, creates release tags.
- **feature/* / other**: Creates build versions with short commit SHA (`sha/7charSHA`).

### Version bump detection (`get_bump_type`)

Parses commit message for keywords:
- `BREAKING CHANGE` or `!` suffix → major
- `feat` → minor
- `fix`, `perf`, `refactor` → patch
- Default → patch

### Changelog generation

`update_changelog()` orchestrates: `get_commits_since_tag()` → `group_commits_by_type()` → `format_changelog_entry()` → writes to `CHANGELOG.md`.

Commits are grouped into: `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`, `misc`.

### Key dependencies

- **GitPython**: Git repo interaction
- **semver**: Version parsing/bumping
- **loguru**: Logging
- **requests**: GitHub API calls

## Tests

Tests are split into:
- `tests/unit/` — mocked, fast; covers changelog and git operations
- `tests/functional/` — uses real git repos via `conftest.py` fixtures; tests full Git Flow scenarios

The `pytest.ini` and `tests/functional/conftest.py` set up environment variables and temp git repos for functional tests.
