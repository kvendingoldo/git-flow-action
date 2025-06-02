import os
import pytest
import tempfile
import shutil
import logging
from pathlib import Path
from git import Repo, GitCommandError
from contextlib import contextmanager
from src.main import (
    get_config,
    git_create_and_push_tag,
    get_semver_version,
    get_new_semver_version,
    create_release_branch,
    get_bump_type,
    main
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestGitFlowScenarios:
    @contextmanager
    def working_directory(self, path):
        """Context manager for changing the working directory"""
        old_dir = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(old_dir)

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary Git repository for testing in /tmp directory"""
        # Create a unique directory name in /tmp
        temp_dir = f"/tmp/git-flow-test-{os.getpid()}"

        # Clean up if directory exists from a previous failed test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # Create the directory
        os.makedirs(temp_dir)

        # Initialize git repository
        repo = Repo.init(temp_dir)

        # Configure git user
        repo.git.config('user.name', 'Test User')
        repo.git.config('user.email', 'test@example.com')

        # Configure git to allow tags
        repo.git.config('--local', 'tag.sort', 'version:refname')
        repo.git.config('--local', 'tag.gpgsign', 'false')

        # Add a dummy origin remote
        repo.create_remote('origin', 'file:///tmp/dummy-remote')

        # Create initial commit
        (Path(temp_dir) / 'README.md').write_text('# Test Repository')
        repo.git.add('README.md')
        repo.git.commit('-m', 'Initial commit')

        yield repo

        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Failed to clean up {temp_dir}: {e}")
            # Don't raise the exception, as it might mask test failures

    def verify_tag(self, repo, expected_tag):
        """Helper method to verify tag existence and value"""
        try:
            # Debug: Print current git status
            logger.debug(f"Current git status:\n{repo.git.status()}")
            logger.debug(f"Current branch: {repo.active_branch.name}")
            logger.debug(f"Current commit: {repo.head.commit.hexsha}")

            # First check if any tags exist
            tags = repo.git.tag('-l').split()
            logger.debug(f"Existing tags: {tags}")

            if not tags:
                # Debug: Check if the commit message matches what we expect
                commit_msg = repo.head.commit.message
                logger.debug(f"Current commit message: {commit_msg}")

                # Debug: Check git config
                config = repo.git.config('--list')
                logger.debug(f"Git config:\n{config}")

                pytest.fail(
                    f"No tags found, expected {expected_tag}. Commit message: {commit_msg}")

            # Then verify the specific tag
            actual_tag = repo.git.describe('--exact-match', '--tags', 'HEAD')
            assert actual_tag == expected_tag, f"Expected tag {expected_tag}, got {actual_tag}"
        except GitCommandError as e:
            if "No names found" in str(e):
                # Debug: Print more information about the error
                logger.debug(f"Git command error: {str(e)}")
                logger.debug(f"Current commit: {repo.head.commit.hexsha}")
                logger.debug(f"Commit message: {repo.head.commit.message}")
                pytest.fail(
                    f"No tags found, expected {expected_tag}. Error: {str(e)}")
            else:
                raise

    def test_scenario1_release_branches_with_prefix(self, temp_repo, monkeypatch):
        """Test scenario: empty repo with release branches and version prefix"""
        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "true")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        config = get_config()

        # Make some commits and create tags
        commits = [
            ("feat: new feature", "v0.1.0"),  # Should create release/0.1
            ("fix: bug fix", "v0.1.1"),       # Should stay on release/0.1
            ("feat: another feature", "v0.2.0"),  # Should create release/0.2
            ("feat! breaking change", "v1.0.0"),  # Should create release/1.0
        ]

        for commit_msg, expected_tag in commits:
            # Create commit
            (Path(temp_repo.working_dir) / 'test.txt').write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)

            # Run main to process the commit
            main()

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Check if release branch was created for minor/major versions
            if expected_tag in ["v0.1.0", "v0.2.0", "v1.0.0"]:
                branch_name = f"release/{expected_tag[1:].rsplit('.', 1)[0]}"
                branches = [b.name for b in temp_repo.branches]
                assert branch_name in branches, f"Release branch {branch_name} was not created"

    def test_scenario2_no_release_branches(self, temp_repo, monkeypatch):
        """Test scenario: empty repo without release branches"""
        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "true")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        config = get_config()

        # Make some commits and create tags
        commits = [
            ("feat: new feature", "0.1.0"),
            ("fix: bug fix", "0.1.1"),
            ("feat: another feature", "0.2.0"),
            ("feat! breaking change", "1.0.0"),
        ]

        for commit_msg, expected_tag in commits:
            # Create commit
            (Path(temp_repo.working_dir) / 'test.txt').write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)

            # Run main to process the commit
            main()

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Verify no release branches were created
            branches = [b.name for b in temp_repo.branches]
            assert "main" in branches, "Main branch should exist"
            assert len(
                branches) == 1, "No additional branches should be created"

    def test_scenario3_enable_release_branches_later(self, temp_repo, monkeypatch):
        """Test scenario: enable release branches after some commits"""
        # Setup environment - initially without release branches
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "true")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        # First phase: make commits without release branches
        initial_commits = [
            ("feat: new feature", "0.1.0"),
            ("fix: bug fix", "0.1.1"),
        ]

        for commit_msg, expected_tag in initial_commits:
            (Path(temp_repo.working_dir) / 'test.txt').write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)
            main()

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Verify no release branches
            branches = [b.name for b in temp_repo.branches]
            assert len(
                branches) == 1, "No release branches should be created yet"

        # Second phase: enable release branches
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")

        # Make more commits that should create release branches
        later_commits = [
            ("feat: another feature", "0.2.0"),  # Should create release/0.2
            ("feat! breaking change", "1.0.0"),  # Should create release/1.0
        ]

        for commit_msg, expected_tag in later_commits:
            (Path(temp_repo.working_dir) / 'test.txt').write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)
            main()

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Verify release branch was created for this commit
            if expected_tag in ["0.2.0", "1.0.0"]:
                branch_name = f"release/{expected_tag.rsplit('.', 1)[0]}"
                branches = [b.name for b in temp_repo.branches]
                assert branch_name in branches, f"Release branch {branch_name} should be created after enabling auto-release"

    def test_scenario4_custom_branch_behavior(self, temp_repo, monkeypatch):
        """Test scenario: custom branch behavior - no tags, SHA version"""
        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "true")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        # Create and switch to a custom branch
        custom_branch = "feature/custom"
        temp_repo.git.checkout('-b', custom_branch)
        logger.debug(f"Created and switched to branch: {custom_branch}")

        # Make a commit on custom branch
        commit_msg = "feat: new feature"
        test_file = Path(temp_repo.working_dir) / 'test.txt'
        test_file.write_text(commit_msg)
        temp_repo.git.add('test.txt')
        temp_repo.git.commit('-m', commit_msg)
        commit_sha = temp_repo.head.commit.hexsha[:7]
        logger.debug(f"Created commit: {commit_sha}")

        # Run main to process the commit
        main()

        # Verify no tags were created
        tags = temp_repo.git.tag('-l').split()
        assert not tags, "No tags should be created on custom branch"

        # Verify we're still on the custom branch
        assert temp_repo.active_branch.name == custom_branch, "Should still be on custom branch"

        # Verify no release branches were created
        branches = [b.name for b in temp_repo.branches]
        assert "main" in branches, "Main branch should exist"
        assert custom_branch in branches, "Custom branch should exist"
        assert len(branches) == 2, "Only main and custom branch should exist"

    def test_scenario5_primary_branch_keywords(self, temp_repo, monkeypatch):
        """Test scenario: all keywords on primary branch with fresh repo for each test case"""
        def setup_fresh_repo():
            """Helper function to set up a fresh repository for each test case"""
            # Clean up the old repo
            shutil.rmtree(temp_repo.working_dir)

            # Create new repo
            repo = Repo.init(temp_repo.working_dir)

            # Configure git user
            repo.git.config('user.name', 'Test User')
            repo.git.config('user.email', 'test@example.com')

            # Configure git to allow tags
            repo.git.config('--local', 'tag.sort', 'version:refname')
            repo.git.config('--local', 'tag.gpgsign', 'false')

            # Add a dummy origin remote
            repo.create_remote('origin', 'file:///tmp/dummy-remote')

            # Create initial commit
            (Path(repo.working_dir) / 'README.md').write_text('# Test Repository')
            repo.git.add('README.md')
            repo.git.commit('-m', 'Initial commit')
            logger.debug("Created fresh repository")

            return repo

        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "false")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        # Test all conventional commit keywords
        keyword_tests = [
            ("feat: new feature", "v0.1.0"),           # Minor version bump
            ("fix: bug fix", "v0.1.1"),                # Patch version bump
            ("chore: update dependencies", "v0.1.2"),   # Patch version bump
            ("docs: update readme", "v0.1.3"),         # Patch version bump
            ("style: format code", "v0.1.4"),          # Patch version bump
            ("refactor: restructure code", "v0.1.5"),  # Patch version bump
            ("perf: improve performance", "v0.1.6"),   # Patch version bump
            ("test: add unit tests", "v0.1.7"),        # Patch version bump
            ("build: update build system", "v0.1.8"),  # Patch version bump
            ("ci: update ci config", "v0.1.9"),        # Patch version bump
            ("revert: revert last change", "v0.1.10"),  # Patch version bump
            ("feat! breaking change", "v1.0.0"),       # Major version bump
        ]

        for commit_msg, expected_tag in keyword_tests:
            logger.debug(f"\nProcessing commit: {commit_msg}")

            # Setup fresh repo for this test case
            repo = setup_fresh_repo()

            # Create commit
            test_file = Path(repo.working_dir) / 'test.txt'
            test_file.write_text(commit_msg)
            repo.git.add('test.txt')
            repo.git.commit('-m', commit_msg)
            logger.debug(f"Created commit: {repo.head.commit.hexsha}")

            # Run main to process the commit
            try:
                with self.working_directory(repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            # Verify tag was created
            self.verify_tag(repo, expected_tag)

        # Test [RELEASE] keyword functionality
        release_tests = [
            ("[RELEASE] 2.0.0", "v2.0.0"),             # Explicit version
            ("[RELEASE] 2.2.0", "v2.2.0"),             # Explicit version
            ("feat: new feature [RELEASE]", "v2.2.0"),  # Implicit minor bump
            ("fix: bug fix [RELEASE]", "v2.2.1"),      # Implicit patch bump
            ("feat! breaking [RELEASE]", "v3.0.0"),    # Implicit major bump
        ]

        for commit_msg, expected_tag in release_tests:
            logger.debug(f"\nProcessing commit: {commit_msg}")

            # Setup fresh repo for this test case
            # repo = setup_fresh_repo()

            # Create commit
            test_file = Path(repo.working_dir) / 'test.txt'
            test_file.write_text(commit_msg)
            repo.git.add('test.txt')
            repo.git.commit('-m', commit_msg)
            logger.debug(f"Created commit: {repo.head.commit.hexsha}")

            # Run main to process the commit
            try:
                with self.working_directory(repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            # Verify tag was created
            self.verify_tag(repo, expected_tag)
