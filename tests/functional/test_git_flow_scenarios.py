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

    def init_repo(self):
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
        logger.debug(f"Initialized git repository in {temp_dir}")

        # Configure git user
        repo.git.config('user.name', 'Test User')
        repo.git.config('user.email', 'test@example.com')
        logger.debug("Configured git user")

        # Configure git to allow tags
        repo.git.config('--local', 'tag.sort', 'version:refname')
        repo.git.config('--local', 'tag.gpgsign', 'false')
        logger.debug("Configured git tag settings")

        # Add a dummy origin remote
        repo.create_remote('origin', 'file:///tmp/dummy-remote')
        logger.debug("Added dummy origin remote")

        # Create initial commit
        (Path(temp_dir) / 'README.md').write_text('# Test Repository')
        repo.git.add('README.md')
        repo.git.commit('-m', 'Initial commit')
        logger.debug("Created initial commit")

        # Get current branch name and force rename to main
        current_branch = repo.active_branch.name
        logger.debug(f"Current branch before rename: {current_branch}")

        # Force rename to main regardless of current name
        repo.git.branch('-m', 'main')
        logger.debug("Renamed branch to 'main'")

        # Verify the rename worked
        new_branch = repo.active_branch.name
        logger.debug(f"Current branch after rename: {new_branch}")
        assert new_branch == 'main', f"Failed to rename branch to main. Current branch is {new_branch}"

        return repo

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

    def check(self, temp_repo, keyword_tests):
        for commit_msg, expected_tag in keyword_tests:
            logger.debug(f"\nProcessing commit: {commit_msg}")

            # Create commit
            test_file = Path(temp_repo.working_dir) / 'test.txt'
            test_file.write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)
            logger.debug(f"Created commit: {temp_repo.head.commit.hexsha}")

            # Run main to process the commit
            try:
                with self.working_directory(temp_repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            self.verify_tag(temp_repo, expected_tag)

    def test_scenario3(self, monkeypatch):
        """
        Test scenario:
            custom branch behavior - no tags, SHA version
        """
        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "true")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        temp_repo = self.init_repo()

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

    def test_scenario4(self, monkeypatch):
        """
        Test scenario:
            Test case with just one release
        """

        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_CANDIDATE", "rc/")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "false")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        temp_repo = self.init_repo()

        keyword_tests = [
            ("feat: new feature", "rc/0.1.0"),
            ("fix: bug fix", "rc/0.1.1"),
            ("chore: update dependencies", "rc/0.2.0"),
            ("hotfix: update readme", "rc/0.2.1"),
            ("style: format code", "rc/0.3.0"),
            ("refactor: restructure code", "rc/0.4.0"),
            ("perf: improve performance", "rc/0.5.0"),
            ("[BUMP-MAJOR] new major version", "rc/1.0.0"),
            ("[hotfix]: update build system", "rc/1.0.1"),
            ("ci: update ci config", "rc/1.1.0"),
            ("revert: revert last change", "rc/1.2.0"),
            ("feat! breaking change", "rc/2.0.0"),
            ("[RELEASE] feat: breaking change", "rc/2.2.0"),
            ("feat: some change2", "rc/2.3.0")
        ]

        self.check(temp_repo, keyword_tests)

    def test_scenario5(self, monkeypatch):
        """
        Test scenario:
            Test INPUT_AUTO_RELEASE_BRANCHES feature for main branch
        """

        monkeypatch.setenv("INPUT_INIT_VERSION", "100.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_CANDIDATE", "rc/")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "false")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        temp_repo = self.init_repo()

        keyword_tests = [
            ("feat: new feature", "100.2.0"),
            ("fix: bug fix", "100.3.0"),
            ("chore: update dependencies", "100.5.0"),
            ("hotfix: update readme", "100.6.0"),
            ("style: format code", "100.8.0"),
            ("refactor: restructure code", "100.10.0"),
            ("[BUMP-MAJOR] new major version", "101.1.0"),
            ("[hotfix]: update build system", "101.2.0"),
            ("ci: update ci config", "101.4.0"),
            ("revert: revert last change", "101.6.0"),
            ("feat! breaking change", "102.1.0"),
            ("[RELEASE] feat: breaking change", "102.3.0"),
        ]

        self.check(temp_repo, keyword_tests)

    def test_scenario6(self, monkeypatch):
        """
        Test scenario:
            Work in feature branch and verify release branch creation
        """
        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "false")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        temp_repo = self.init_repo()

        # Create and switch to a feature branch
        feature_branch = "feature/new-feature"
        temp_repo.git.checkout('-b', feature_branch)
        logger.debug(f"Created and switched to branch: {feature_branch}")

        # Make commits on feature branch
        feature_commits = [
            # No tag or release branch expected
            ("feat: implement new feature", None, None),
            # No tag or release branch expected
            ("fix: fix feature bug", None, None),
            # No tag or release branch expected
            ("feat: add more functionality", None, None),
        ]

        for commit_msg, _, _ in feature_commits:
            logger.debug(f"\nProcessing feature branch commit: {commit_msg}")
            test_file = Path(temp_repo.working_dir) / 'test.txt'
            test_file.write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)

            # Run main to process the commit
            try:
                with self.working_directory(temp_repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            # Verify no tags were created on feature branch
            tags = temp_repo.git.tag('-l').split()
            assert not tags, f"Tags should not be created on feature branch for commit: {commit_msg}"

        # Switch back to main branch
        temp_repo.git.checkout('main')
        logger.debug("Switched back to main branch")

        # Merge feature branch into main
        temp_repo.git.merge(feature_branch, '--no-ff',
                            '-m', 'Merge feature branch')
        logger.debug("Merged feature branch into main")

        # Map of commits to their expected tags and release branches
        # Format: (commit_message, expected_tag, expected_release_branch)
        main_commits = [
            ("feat: new feature after merge", "v0.2.0", "release/0.1"),
            ("fix: bug fix", "v0.3.0", "release/0.2"),
            ("feat: another feature", "v0.5.0", "release/0.4"),
            ("feat! breaking change", "v1.1.0", "release/1.0"),
        ]

        for commit_msg, expected_tag, expected_release_branch in main_commits:
            logger.debug(f"\nProcessing main branch commit: {commit_msg}")
            test_file = Path(temp_repo.working_dir) / 'test.txt'
            test_file.write_text(commit_msg)
            temp_repo.git.add('test.txt')
            temp_repo.git.commit('-m', commit_msg)

            # Run main to process the commit
            try:
                with self.working_directory(temp_repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Verify release branch was created
            branches = [b.name for b in temp_repo.branches]
            assert expected_release_branch in branches, f"Release branch {expected_release_branch} was not created for commit: {commit_msg}"
            logger.debug(
                f"Verified release branch {expected_release_branch} exists")

        # Verify final state
        branches = [b.name for b in temp_repo.branches]
        expected_branches = {
            'main',
            feature_branch,
            'release/0.1',
            'release/0.2',
            'release/0.4',
            'release/1.0'
        }
        assert set(
            branches) == expected_branches, f"Expected branches {expected_branches}, got {set(branches)}"

    def test_scenario7(self, monkeypatch):
        """
        Test scenario:
            Work in release branches and verify versioning
        """
        # Setup environment
        monkeypatch.setenv("INPUT_INIT_VERSION", "0.0.0")
        monkeypatch.setenv("INPUT_PRIMARY_BRANCH", "main")
        monkeypatch.setenv("INPUT_TAG_PREFIX_RELEASE", "v")
        monkeypatch.setenv("INPUT_AUTO_RELEASE_BRANCHES", "main")
        monkeypatch.setenv("INPUT_ENABLE_GIT_PUSH", "false")
        monkeypatch.setenv("INPUT_ENABLE_GITHUB_RELEASE", "false")

        temp_repo = self.init_repo()

        # First create a release branch from main
        temp_repo.git.checkout('main')
        test_file = Path(temp_repo.working_dir) / 'main.txt'
        test_file.write_text("Initial main work")
        temp_repo.git.add('main.txt')
        temp_repo.git.commit('-m', 'feat: initial work')

        # Run main to create first release branch
        with self.working_directory(temp_repo.working_dir):
            main()

        # Verify first release branch was created
        release_branch = "release/0.1"
        branches = [b.name for b in temp_repo.branches]
        assert release_branch in branches, f"Release branch {release_branch} was not created"
        logger.debug(f"Verified release branch {release_branch} exists")

        # Switch to release branch
        temp_repo.git.checkout(release_branch)
        logger.debug(f"Switched to release branch: {release_branch}")

        # Make commits on release branch
        release_commits = [
            ("fix: fix release issue", "v0.1.1"),
            ("fix: another fix", "v0.1.2"),
            ("docs: update release docs", "v0.1.3"),
        ]

        for commit_msg, expected_tag in release_commits:
            logger.debug(
                f"\nProcessing commit on {release_branch}: {commit_msg}")

            # Create or update file
            file_path = Path(temp_repo.working_dir) / 'release.txt'
            file_path.write_text(commit_msg)
            temp_repo.git.add('release.txt')
            temp_repo.git.commit('-m', commit_msg)
            logger.debug(f"Created commit: {temp_repo.head.commit.hexsha}")

            # Run main to process the commit
            try:
                with self.working_directory(temp_repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Verify we're still on the release branch
            assert temp_repo.active_branch.name == release_branch, f"Should still be on {release_branch}"

        # Switch back to main
        temp_repo.git.checkout('main')
        logger.debug("Switched back to main branch")

        # Create another release branch
        test_file = Path(temp_repo.working_dir) / 'main.txt'
        test_file.write_text("New feature work")
        temp_repo.git.add('main.txt')
        temp_repo.git.commit('-m', 'feat: new feature')

        # Run main to create second release branch
        with self.working_directory(temp_repo.working_dir):
            main()

        # Verify second release branch was created
        new_release_branch = "release/0.3"
        branches = [b.name for b in temp_repo.branches]
        assert new_release_branch in branches, f"Release branch {new_release_branch} was not created"
        logger.debug(f"Verified release branch {new_release_branch} exists")

        # Switch to new release branch
        temp_repo.git.checkout(new_release_branch)
        logger.debug(f"Switched to release branch: {new_release_branch}")

        # Make commits on new release branch
        new_release_commits = [
            ("fix: fix in new release", "v0.3.1"),
            ("fix: critical fix", "v0.3.2"),
            ("docs: update new release", "v0.3.3"),
        ]

        for commit_msg, expected_tag in new_release_commits:
            logger.debug(
                f"\nProcessing commit on {new_release_branch}: {commit_msg}")

            # Create or update file
            file_path = Path(temp_repo.working_dir) / 'new_release.txt'
            file_path.write_text(commit_msg)
            temp_repo.git.add('new_release.txt')
            temp_repo.git.commit('-m', commit_msg)
            logger.debug(f"Created commit: {temp_repo.head.commit.hexsha}")

            # Run main to process the commit
            try:
                with self.working_directory(temp_repo.working_dir):
                    main()
                logger.debug("main() completed successfully")
            except Exception as e:
                logger.error(f"Error in main(): {str(e)}", exc_info=True)
                raise

            # Verify tag was created
            self.verify_tag(temp_repo, expected_tag)

            # Verify we're still on the release branch
            assert temp_repo.active_branch.name == new_release_branch, f"Should still be on {new_release_branch}"

        # Verify final state
        branches = [b.name for b in temp_repo.branches]
        expected_branches = {'main', release_branch, new_release_branch}
        assert set(
            branches) == expected_branches, f"Expected branches {expected_branches}, got {set(branches)}"

        # Verify we're still on the new release branch
        assert temp_repo.active_branch.name == new_release_branch, f"Should still be on {new_release_branch}"
