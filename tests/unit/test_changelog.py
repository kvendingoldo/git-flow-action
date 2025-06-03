"""Unit tests for changelog operations."""

import pytest
from pathlib import Path
from src.main import update_changelog


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


def test_update_changelog_new_version(temp_changelog):
    """Test adding a new version to changelog."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0"

    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")
    assert "## v1.0.0" in content
    assert "## v0.9.0" in content


def test_update_changelog_existing_version(temp_changelog):
    """Test updating an existing version in changelog."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.0.0"  # Already exists

    # This should not raise an error, but should add a duplicate entry
    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.count(f"## {new_tag}") == 2


def test_update_changelog_invalid_version(temp_changelog):
    """Test updating changelog with invalid version format."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "invalid-version"

    # This should not raise an error, but should add the tag as is
    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")


def test_update_changelog_empty_changes(temp_changelog):
    """Test updating changelog with empty changes."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0"

    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")
    # Should not add any empty lines after the new version


def test_update_changelog_nonexistent_file(tmp_path):
    """Test updating non-existent changelog file."""
    changelog_file = tmp_path / "nonexistent.md"
    config = {"paths": {"changelog": str(changelog_file)}}
    new_tag = "v1.0.0"

    update_changelog(config, new_tag)

    assert changelog_file.exists()
    content = changelog_file.read_text()
    assert content == f"## {new_tag}\n"


def test_update_changelog_empty_file(tmp_path):
    """Test updating empty changelog file."""
    changelog_file = tmp_path / "empty.md"
    changelog_file.touch()
    config = {"paths": {"changelog": str(changelog_file)}}
    new_tag = "v1.0.0"

    update_changelog(config, new_tag)

    content = changelog_file.read_text()
    assert content == f"## {new_tag}\n"


def test_update_changelog_preserves_formatting(temp_changelog):
    """Test that existing formatting is preserved."""
    original_content = temp_changelog.read_text()
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0"

    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")
    # Check that the rest of the content is preserved exactly
    assert content[content.find(
        "## v1.0.0"):] == original_content[original_content.find("## v1.0.0"):]


def test_update_changelog_with_date(temp_changelog):
    """Test updating changelog with version and date."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0 (2024-01-01)"

    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")


def test_update_changelog_with_invalid_date(temp_changelog):
    """Test updating changelog with invalid date format."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0 (invalid-date)"

    # This should not raise an error
    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")


def test_update_changelog_with_special_characters(temp_changelog):
    """Test updating changelog with special characters in version."""
    config = {"paths": {"changelog": str(temp_changelog)}}
    new_tag = "v1.1.0-beta.1+20240101"

    update_changelog(config, new_tag)

    content = temp_changelog.read_text()
    assert content.startswith(f"## {new_tag}\n")
    # Check that special characters are preserved
    assert "v1.1.0-beta.1+20240101" in content
