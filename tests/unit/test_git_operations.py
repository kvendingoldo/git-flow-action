"""Unit tests for Git operations."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from git import Repo, GitCommandError
import semver
import subprocess

# Import the functions we want to test
from src.main import (
    git_create_and_push_tag,
    get_semver_version,
    get_new_semver_version,
    create_release_branch,
    get_bump_type,
    git
)


@pytest.fixture
def mock_git():
    """Mock git command execution."""
    with patch('subprocess.check_output') as mock_check_output:
        yield mock_check_output


@pytest.fixture
def mock_repo():
    """Mock git repository."""
    repo = MagicMock()
    repo.git = MagicMock()
    return repo


@pytest.fixture
def basic_config():
    """Fixture that provides basic configuration"""
    return {
        "init_version": "0.0.0",
        "primary_branch": "main",
        "tag_prefix": {
            "candidate": "rc/",
            "release": ""
        },
        "features": {
            "enable_git_push": "true",
            "enable_github_release": "true",
            "enable_custom_branch": "true"
        },
        "keywords": {
            "patch_bump": ['[hotfix]', '[fix]', 'hotfix:', 'fix:'],
            "major_bump": ['[BUMP-MAJOR]', 'bump-major', 'feat!']
        }
    }


class TestGitTagOperations:
    def test_git_create_and_push_tag_with_push_enabled(self, mock_repo, basic_config):
        """Test tag creation and push when push is enabled"""
        tag = "v1.0.0"

        git_create_and_push_tag(basic_config, mock_repo, tag)

        # Verify tag was created
        mock_repo.git.tag.assert_called_once_with(tag, 'HEAD')
        # Verify tag was pushed
        mock_repo.git.push.assert_called_once_with(
            '--tags', 'origin', f'refs/tags/{tag}')

    def test_git_create_and_push_tag_with_push_disabled(self, mock_repo, basic_config):
        """Test tag creation without push when push is disabled"""
        basic_config["features"]["enable_git_push"] = "false"
        tag = "v1.0.0"

        git_create_and_push_tag(basic_config, mock_repo, tag)

        # Verify tag was created
        mock_repo.git.tag.assert_called_once_with(tag, 'HEAD')
        # Verify tag was not pushed
        mock_repo.git.push.assert_not_called()

    def test_git_create_and_push_tag_failure(self, mock_repo, basic_config):
        """Test tag creation failure handling"""
        tag = "v1.0.0"
        mock_repo.git.tag.side_effect = GitCommandError(
            "tag", "Failed to create tag")

        with pytest.raises(GitCommandError):
            git_create_and_push_tag(basic_config, mock_repo, tag)


class TestVersionManagement:
    def test_get_semver_version_from_tag(self, basic_config):
        """Test parsing semantic version from git tag"""
        tag = "rc/1.2.3"
        version = get_semver_version(basic_config, tag)

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_get_semver_version_from_initial(self, basic_config):
        """Test getting initial version when no tag exists"""
        version = get_semver_version(basic_config)

        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_get_new_semver_version_patch(self, basic_config):
        """Test patch version bump"""
        current_version = semver.VersionInfo(1, 2, 3)
        new_version = get_new_semver_version(
            basic_config, str(current_version), 'patch')

        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4

    def test_get_new_semver_version_minor(self, basic_config):
        """Test minor version bump"""
        current_version = semver.VersionInfo(1, 2, 3)
        new_version = get_new_semver_version(
            basic_config, str(current_version), 'minor')

        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_get_new_semver_version_major(self, basic_config):
        """Test major version bump"""
        current_version = semver.VersionInfo(1, 2, 3)
        new_version = get_new_semver_version(
            basic_config, str(current_version), 'major')

        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0


class TestBranchOperations:
    def test_create_release_branch_success(self, mock_repo, basic_config):
        """Test successful release branch creation"""
        new_version = semver.VersionInfo(1, 2, 3)

        create_release_branch(basic_config, mock_repo, new_version)

        # Verify branch was created
        mock_repo.git.checkout.assert_called_once_with('-b', 'release/1.2')
        # Verify branch was pushed
        mock_repo.git.push.assert_called_once_with(
            '-u', 'origin', 'release/1.2')

    def test_create_release_branch_without_push(self, mock_repo, basic_config):
        """Test release branch creation without push"""
        basic_config["features"]["enable_git_push"] = "false"
        new_version = semver.VersionInfo(1, 2, 3)

        create_release_branch(basic_config, mock_repo, new_version)

        # Verify branch was created
        mock_repo.git.checkout.assert_called_once_with('-b', 'release/1.2')
        # Verify branch was not pushed
        mock_repo.git.push.assert_not_called()

    def test_create_release_branch_failure(self, mock_repo, basic_config):
        """Test release branch creation failure"""
        new_version = semver.VersionInfo(1, 2, 3)
        mock_repo.git.checkout.side_effect = GitCommandError(
            "checkout", "Failed to create branch")

        # Should not raise exception, just log the error
        create_release_branch(basic_config, mock_repo, new_version)

        mock_repo.git.checkout.assert_called_once_with('-b', 'release/1.2')
        mock_repo.git.push.assert_not_called()


class TestBumpTypeDetection:
    def test_get_bump_type_major(self, basic_config):
        """Test major version bump detection"""
        commit_message = "feat! add new feature"
        bump_type = get_bump_type(basic_config, commit_message)
        assert bump_type == 'major'

    def test_get_bump_type_patch(self, basic_config):
        """Test patch version bump detection"""
        commit_message = "fix: bug fix"
        bump_type = get_bump_type(basic_config, commit_message)
        assert bump_type == 'patch'

    def test_get_bump_type_minor(self, basic_config):
        """Test minor version bump detection (default)"""
        commit_message = "feat: new feature"
        bump_type = get_bump_type(basic_config, commit_message)
        assert bump_type == 'minor'

    def test_get_bump_type_case_insensitive(self, basic_config):
        """Test case-insensitive bump type detection"""
        commit_message = "FIX: bug fix"
        bump_type = get_bump_type(basic_config, commit_message)
        assert bump_type == 'patch'


def test_git_success(mock_git):
    """Test successful git command execution."""
    mock_git.return_value = b"success"
    result = git("status")
    assert result == "success"
    mock_git.assert_called_once_with(["git", "status"])


def test_git_failure(mock_git):
    """Test git command failure."""
    mock_git.side_effect = subprocess.CalledProcessError(1, "git status")
    with pytest.raises(subprocess.CalledProcessError):
        git("status")


def test_git_create_and_push_tag_success(mock_repo):
    """Test successful tag creation and push."""
    config = {
        "features": {
            "enable_git_push": "true"
        }
    }
    tag = "v1.0.0"

    git_create_and_push_tag(config, mock_repo, tag)

    mock_repo.git.tag.assert_called_once_with(tag, "HEAD")
    mock_repo.git.push.assert_called_once_with(
        '--tags', 'origin', f"refs/tags/{tag}")


def test_git_create_and_push_tag_no_push(mock_repo):
    """Test tag creation without push."""
    config = {
        "features": {
            "enable_git_push": "false"
        }
    }
    tag = "v1.0.0"

    git_create_and_push_tag(config, mock_repo, tag)

    mock_repo.git.tag.assert_called_once_with(tag, "HEAD")
    mock_repo.git.push.assert_not_called()


def test_git_create_and_push_tag_with_sha(mock_repo):
    """Test tag creation with specific SHA."""
    config = {
        "features": {
            "enable_git_push": "true"
        }
    }
    tag = "v1.0.0"
    sha = "abc123"

    git_create_and_push_tag(config, mock_repo, tag, sha)

    mock_repo.git.tag.assert_called_once_with(tag, sha)
    mock_repo.git.push.assert_called_once_with(
        '--tags', 'origin', f"refs/tags/{tag}")


def test_git_create_and_push_tag_failure(mock_repo):
    """Test tag creation failure."""
    config = {
        "features": {
            "enable_git_push": "true"
        }
    }
    tag = "v1.0.0"
    mock_repo.git.tag.side_effect = GitCommandError(
        "tag", "Tag already exists")

    with pytest.raises(GitCommandError):
        git_create_and_push_tag(config, mock_repo, tag)


def test_git_push_failure(mock_repo):
    """Test tag push failure."""
    config = {
        "features": {
            "enable_git_push": "true"
        }
    }
    tag = "v1.0.0"
    mock_repo.git.push.side_effect = GitCommandError("push", "Push failed")

    with pytest.raises(GitCommandError):
        git_create_and_push_tag(config, mock_repo, tag)


def test_git_command_with_multiple_args(mock_git):
    """Test git command with multiple arguments."""
    mock_git.return_value = b"success"
    result = git("commit", "-m", "test message")
    assert result == "success"
    mock_git.assert_called_once_with(["git", "commit", "-m", "test message"])


def test_git_command_with_special_chars(mock_git):
    """Test git command with special characters in arguments."""
    mock_git.return_value = b"success"
    result = git("commit", "-m", "test message with spaces and @#$%")
    assert result == "success"
    mock_git.assert_called_once_with(
        ["git", "commit", "-m", "test message with spaces and @#$%"])


def test_git_command_with_empty_args(mock_git):
    """Test git command with empty arguments."""
    mock_git.return_value = b"success"
    result = git("")
    assert result == "success"
    mock_git.assert_called_once_with(["git", ""])


def test_git_command_with_none_args(mock_git):
    """Test git command with None arguments."""
    mock_git.return_value = b"success"
    # None is not a valid argument type
    with pytest.raises(TypeError, match="Git command arguments must be strings, got <class 'NoneType'>"):
        git(None)


def test_git_command_with_invalid_args(mock_git):
    """Test git command with invalid argument types."""
    mock_git.return_value = b"success"
    with pytest.raises(TypeError):
        git(123)  # Non-string argument
