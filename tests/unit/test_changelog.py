"""Unit tests for changelog operations."""

import pytest
from pathlib import Path
from src.main import update_changelog, group_commits_by_type, generate_changelog_between_tags


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
    """Test grouping feature commits, including special characters."""
    commits = [
        "abc123 feat(auth): add login functionality",
        "def456 feature(ui): enhance button styles",
        "789012 feat: add dark mode toggle",
        "xyz987 feat(api+meta): support v1.0.0+meta",
        "uvw654 feat: handle special chars in version v1.2.3-beta"
    ]
    
    result = group_commits_by_type(commits)
    
    assert len(result['feature']) == 5
    assert "feat(auth): add login functionality" in result['feature'][0]
    assert "feature(ui): enhance button styles" in result['feature'][1]
    assert "feat: add dark mode toggle" in result['feature'][2]
    assert "feat(api+meta): support v1.0.0+meta" in result['feature'][3]
    assert "feat: handle special chars in version v1.2.3-beta" in result['feature'][4]


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


# ---------------------------------------------------------------------------
# Helpers shared by generate_changelog_between_tags tests
# ---------------------------------------------------------------------------

class _FakeTagCommit:
    def __init__(self, hexsha, committed_date, message="chore: placeholder"):
        self.hexsha = hexsha
        self.committed_date = committed_date
        self.message = message


class _FakeTagRef:
    """Lightweight tag stand-in."""
    def __init__(self, name, hexsha, committed_date, message="chore: placeholder"):
        self.name = name
        self.tag = None  # lightweight
        self.commit = _FakeTagCommit(hexsha, committed_date, message)


class _FakeAnnotatedTagRef(_FakeTagRef):
    """Annotated tag stand-in."""
    class _Ann:
        def __init__(self, tagged_date):
            self.tagged_date = tagged_date

    def __init__(self, name, hexsha, committed_date, tagged_date, message="chore: placeholder"):
        super().__init__(name, hexsha, committed_date, message)
        self.tag = self._Ann(tagged_date)


class _FakeCommit:
    def __init__(self, hexsha, message):
        self.hexsha = hexsha
        self.message = message


def _make_repo(tag_refs, commits_by_revision):
    class _FakeGit:
        def __init__(self, names):
            self._names = names
        def tag(self, *args):
            if '--merged' in args:
                return '\n'.join(self._names)
            return ''

    class _FakeRepo:
        def __init__(self):
            self.tags = tag_refs
            self.git = _FakeGit([t.name for t in tag_refs])
        def iter_commits(self, revision):
            if revision not in commits_by_revision:
                raise Exception(f"Unknown revision: {revision}")
            return commits_by_revision[revision]

    return _FakeRepo()


# ---------------------------------------------------------------------------
# Tests for generate_changelog_between_tags
# ---------------------------------------------------------------------------

def test_generate_changelog_between_tags_no_tags():
    repo = _make_repo([], {})
    result = generate_changelog_between_tags(repo)
    assert "No tags" in result


def test_generate_changelog_between_tags_single_tag():
    tag = _FakeTagRef("v1.0.0", "a" * 40, 1000)
    commits = [
        _FakeCommit("abc1234" + "x" * 33, "feat: initial feature"),
        _FakeCommit("def5678" + "x" * 33, "fix: early fix"),
    ]
    repo = _make_repo([tag], {"v1.0.0": commits})
    result = generate_changelog_between_tags(repo)
    assert "## v1.0.0 -" in result
    assert "### Features" in result
    assert "initial feature" in result
    assert "### Bug Fixes" in result
    assert "early fix" in result


def test_generate_changelog_between_tags_two_tags():
    tag_old = _FakeTagRef("v1.0.0", "a" * 40, 1000)
    tag_new = _FakeTagRef("v1.1.0", "b" * 40, 2000)
    commits = [
        _FakeCommit("c" * 40, "feat: new thing"),
        _FakeCommit("d" * 40, "fix: patch issue"),
    ]
    repo = _make_repo([tag_old, tag_new], {"v1.0.0..v1.1.0": commits})
    result = generate_changelog_between_tags(repo)
    assert "## v1.1.0 -" in result
    assert "new thing" in result
    assert "patch issue" in result


def test_generate_changelog_between_tags_sorts_by_date_not_name():
    """v1.10.0 is newest by date even though v1.9.0 > v1.10.0 lexicographically."""
    tag_v1_10 = _FakeTagRef("v1.10.0", "a" * 40, 3000)
    tag_v1_9  = _FakeTagRef("v1.9.0",  "b" * 40, 2000)
    tag_v1_0  = _FakeTagRef("v1.0.0",  "c" * 40, 1000)
    commits = [_FakeCommit("e" * 40, "feat: ten")]
    repo = _make_repo(
        [tag_v1_10, tag_v1_9, tag_v1_0],
        {"v1.9.0..v1.10.0": commits},
    )
    result = generate_changelog_between_tags(repo)
    assert "## v1.10.0 -" in result
    assert "ten" in result


def test_generate_changelog_between_tags_annotated_uses_tagged_date():
    """Annotated tags are sorted by tagged_date, not commit committed_date."""
    tag_old = _FakeAnnotatedTagRef("v2.0.0", "a" * 40, committed_date=5000, tagged_date=1000)
    tag_new = _FakeAnnotatedTagRef("v2.1.0", "b" * 40, committed_date=4000, tagged_date=2000)
    commits = [_FakeCommit("c" * 40, "chore: after tag")]
    repo = _make_repo([tag_old, tag_new], {"v2.0.0..v2.1.0": commits})
    result = generate_changelog_between_tags(repo)
    assert "## v2.1.0 -" in result


def test_generate_changelog_between_tags_empty_range():
    """Same-commit tags produce an informative empty-range message."""
    tag1 = _FakeTagRef("v1.0.0", "a" * 40, 1000)
    tag2 = _FakeTagRef("v1.0.1", "a" * 40, 2000)
    repo = _make_repo([tag1, tag2], {"v1.0.0..v1.0.1": []})
    result = generate_changelog_between_tags(repo)
    assert "No commits" in result


def test_generate_changelog_between_tags_merge_commits_included():
    tag_old = _FakeTagRef("v1.0.0", "a" * 40, 1000)
    tag_new = _FakeTagRef("v1.1.0", "b" * 40, 2000)
    commits = [
        _FakeCommit("f" * 40, "Merge pull request #42 from org/feature-x"),
        _FakeCommit("c" * 40, "feat: actual feature"),
    ]
    repo = _make_repo([tag_old, tag_new], {"v1.0.0..v1.1.0": commits})
    result = generate_changelog_between_tags(repo)
    assert "Merge pull request" in result


def test_generate_changelog_between_tags_output_format():
    """Output has version header and sections in correct order."""
    import re
    tag_old = _FakeTagRef("v3.0.0", "a" * 40, 1000)
    tag_new = _FakeTagRef("v3.1.0", "b" * 40, 2000)
    commits = [
        _FakeCommit("1234567" + "x" * 33, "feat: add new thing"),
        _FakeCommit("abcdefg" + "x" * 33, "fix: patch issue"),
        _FakeCommit("fedcbag" + "x" * 33, "chore: update deps"),
    ]
    repo = _make_repo([tag_old, tag_new], {"v3.0.0..v3.1.0": commits})
    result = generate_changelog_between_tags(repo)
    assert re.match(r"^## v3\.1\.0 - \d{4}-\d{2}-\d{2}", result)
    sections = [
        "### Features", "### Bug Fixes", "### Chores", "### Documentation",
        "### Refactors", "### Performance Improvements", "### Tests", "### Miscellaneous",
    ]
    indices = [result.find(s) for s in sections if result.find(s) != -1]
    assert indices == sorted(indices), "Sections out of order"
