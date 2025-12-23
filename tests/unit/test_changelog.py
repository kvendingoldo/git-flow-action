"""Unit tests for changelog operations."""

import pytest
from pathlib import Path
from src.main import update_changelog, group_commits_by_type


@pytest.fixture
def temp_changelog(tmp_path):
    """Create a temporary changelog file for testing."""
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("""# Changelog

## v1.0.0
- Initial release

## v0.9.0
- Beta release
""")
    return changelog_file


def _dummy_repo_with_commit():
    class DummyCommit:
        def __init__(self, hexsha, message):
            self.hexsha = hexsha
            self.message = message
    class DummyRepo:
        def iter_commits(self, rev):
            return [DummyCommit('abc1234', 'feat: dummy commit for changelog')]
    return DummyRepo()

def test_update_changelog_new_version(temp_changelog):
    """Test adding a new version to changelog."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag} - ")
    assert "## v1.0.0" in content
    assert "## v0.9.0" in content


def test_update_changelog_existing_version(temp_changelog):
    """Test updating an existing version in changelog."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.0.0"  # Already exists
    repo = _dummy_repo_with_commit()
    tag_last = "v0.9.0"

    # This should not raise an error, but should add a duplicate entry
    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.count(f"## {new_tag} - ") == 1


def test_update_changelog_invalid_version(temp_changelog):
    """Test updating changelog with invalid version format."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "invalid-version"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    # This should not raise an error, but should add the tag as is
    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag} - ")


def test_update_changelog_empty_changes(temp_changelog):
    """Test updating changelog with empty changes."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag} - ")
    # Should not add any empty lines after the new version


def test_update_changelog_nonexistent_file(tmp_path):
    """Test updating non-existent changelog file."""
    changelog_file = tmp_path / "nonexistent.md"
    config = {"paths": {"changelog": str(changelog_file)}}
    new_tag = "v1.0.0"
    repo = _dummy_repo_with_commit()  # Always returns a commit
    tag_last = "v0.9.0"

    update_changelog(config, new_tag, repo, tag_last)

    assert changelog_file.exists()
    content = changelog_file.read_text()
    assert content.startswith(f"## {new_tag} - ")


def test_update_changelog_empty_file(tmp_path):
    """Test updating empty changelog file."""
    changelog_file = tmp_path / "empty.md"
    changelog_file.touch()
    config = {"paths": {"changelog": str(changelog_file)}}
    new_tag = "v1.0.0"
    repo = _dummy_repo_with_commit()  # Always returns a commit
    tag_last = "v0.9.0"

    update_changelog(config, new_tag, repo, tag_last)

    content = changelog_file.read_text()
    assert content.startswith(f"## {new_tag} - ")


def test_update_changelog_complex_scenario(tmp_path, mocker):
    """Test update_changelog with a complex set of commits and tags."""
    from datetime import datetime
    import re
    # Prepare a fake repo object
    class FakeCommit:
        def __init__(self, hexsha, message):
            self.hexsha = hexsha
            self.message = message
    class FakeRepo:
        def iter_commits(self, rev):
            # Simulate commits between tags
            return [
                FakeCommit('a1b2c3d', 'feat(auth): add login'),
                FakeCommit('b2c3d4e', 'fix(auth): handle token expiry'),
                FakeCommit('c3d4e5f', 'chore: update deps'),
                FakeCommit('d4e5f6g', 'docs: update API docs'),
                FakeCommit('e5f6g7h', 'refactor(core): cleanup'),
                FakeCommit('f6g7h8i', 'perf: optimize queries'),
                FakeCommit('g7h8i9j', 'test: add integration tests'),
                FakeCommit('h8i9j0k', 'style: fix lint issues'),
                FakeCommit('i9j0k1l', 'feat(ui): add dark mode'),
                FakeCommit('j0k1l2m', 'misc: update copyright'),
                FakeCommit('k1l2m3n', 'fix: general bugfix'),
            ]
    repo = FakeRepo()
    changelog_file = tmp_path / "COMPLEX_CHANGELOG.md"
    config = {"paths": {"changelog": str(changelog_file)}}
    new_tag = "v2.0.0"
    tag_last = "v1.0.0"

    # Patch datetime to return a fixed date
    mocker.patch("src.main.datetime.datetime", autospec=True)
    from src import main as main_mod
    main_mod.datetime.datetime.now.return_value.strftime.return_value = "2025-07-30"

    # Run changelog update
    main_mod.update_changelog(config, new_tag, repo, tag_last)

    content = changelog_file.read_text()
    # Check version/date header
    assert f"## {new_tag} - 2025-07-30" in content
    # Check all sections present
    assert "### Features" in content
    assert "### Bug Fixes" in content
    assert "### Chores" in content
    assert "### Documentation" in content
    assert "### Refactors" in content
    assert "### Performance Improvements" in content
    assert "### Tests" in content
    assert "### Miscellaneous" in content
    # Check commit messages in correct sections
    assert "add login" in content
    assert "add dark mode" in content
    assert "handle token expiry" in content
    assert "general bugfix" in content
    assert "update deps" in content
    assert "update API docs" in content
    assert "cleanup" in content
    assert "optimize queries" in content
    assert "add integration tests" in content
    assert "fix lint issues" in content  # Should be in Miscellaneous
    assert "update copyright" in content
    # Check order: Features first, then Bug Fixes, etc.
    section_indices = [
        content.index("### Features"),
        content.index("### Bug Fixes"),
        content.index("### Chores"),
        content.index("### Documentation"),
        content.index("### Refactors"),
        content.index("### Performance Improvements"),
        content.index("### Tests"),
        content.index("### Miscellaneous")
    ]
    assert section_indices == sorted(section_indices)


def test_update_changelog_preserves_formatting(temp_changelog):
    """Test that existing formatting is preserved."""
    original_content = temp_changelog.read_text()
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag} - ")
    # Should preserve the original formatting
    assert "# Changelog" in content
    assert original_content in content


def test_update_changelog_with_date(temp_changelog):
    """Test updating changelog with version and date."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0 (2024-01-01)"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag} - ")


def test_update_changelog_with_invalid_date(temp_changelog):
    """Test updating changelog with invalid date format."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0 (invalid-date)"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    # This should not raise an error
    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag} - ")


def test_update_changelog_with_special_characters(temp_changelog):
    """Test updating changelog with special characters in version."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.0.0+meta"
    repo = _dummy_repo_with_commit()
    tag_last = "v1.0.0"

    update_changelog(config, new_tag, repo, tag_last)

    content = temp_changelog.read_text()
    assert f"## {new_tag} - " in content
    assert "## v1.0.0" in content  # Original entry should still be there


def test_group_commits_by_type_feature():
    """Test grouping feature commits."""
    commits = [
        "abc123 feat(auth): add login functionality",
        "def456 feature(ui): enhance button styles",
        "789012 feat: add dark mode toggle"
    ]
    
    result = group_commits_by_type(commits)
    
    assert len(result['feature']) == 3
    assert "feat(auth): add login functionality" in result['feature'][0]
    assert "feature(ui): enhance button styles" in result['feature'][1]
    assert "feat: add dark mode toggle" in result['feature'][2]


def test_group_commits_by_type_fix():
    """Test grouping fix commits."""
    commits = [
        "abc123 fix(auth): handle expired tokens",
        "def456 bugfix(api): fix 500 error on null input"
    ]
    
    result = group_commits_by_type(commits)
    
    assert len(result['fix']) == 2
    assert "fix(auth): handle expired tokens" in result['fix'][0]
    assert "bugfix(api): fix 500 error on null input" in result['fix'][1]


def test_group_commits_by_type_other_types():
    """Test grouping other commit types."""
    commits = [
        "abc123 chore: update dependencies",
        "def456 docs: update README",
        "789012 refactor: clean up code",
        "345678 perf: optimize database queries",
        "901234 test: add unit tests",
        "567890 style: fix linting issues"
    ]
    
    result = group_commits_by_type(commits)
    
    assert len(result['chore']) == 1
    assert len(result['docs']) == 1
    assert len(result['refactor']) == 1
    assert len(result['perf']) == 1
    assert len(result['test']) == 1
    assert "style: fix linting issues" in result['misc'][0]  # style not in our mapping


def test_group_commits_by_type_malformed():
    """Test handling of malformed commit messages."""
    commits = [
        "abc123",  # No message
        "def456 : no type",  # Empty type
        "789012 (scope): missing type",  # Missing type
        "345678 invalid-type: unknown type"  # Unknown type
    ]
    
    result = group_commits_by_type(commits)
    
    assert len(result['misc']) == 4  # All should go to misc


def test_group_commits_by_type_mixed():
    """Test grouping with mixed commit types."""
    commits = [
        "abc123 feat(auth): add login",
        "def456 fix(auth): handle token expiry",
        "789012 chore: update deps",
        "345678 docs: update API docs",
        "901234 feat(ui): add dark mode"
    ]
    
    result = group_commits_by_type(commits)
    
    assert len(result['feature']) == 2
    assert len(result['fix']) == 1
    assert len(result['chore']) == 1
    assert len(result['docs']) == 1
    assert len(result['misc']) == 0  # No unexpected types
    
    # Verify the content is preserved
    assert "feat(auth): add login" in result['feature'][0]
    assert "fix(auth): handle token expiry" in result['fix'][0]
    assert "chore: update deps" in result['chore'][0]
    assert "docs: update API docs" in result['docs'][0]
    assert "feat(ui): add dark mode" in result['feature'][1]
