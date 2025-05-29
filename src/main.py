#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import re
import os
import sys
import logging
import subprocess
import requests
import semver
import git as real_git

from git import GitCommandError


def git(*args):
    output = subprocess.check_output(["git"] + list(args)).decode().strip()
    logging.info("Git command %s produced output:\n%s\n=======", args, output)
    return output


def git_create_and_push_tag(config, repo, tag, sha="HEAD"):
    repo.git.tag(tag, sha)

    if config["features"]["enable_git_push"] == "true":
        repo.git.push('--tags', 'origin', 'refs/tags/{tag}'.format(tag=tag))
        logging.info("Git tag push has been pushed")
    else:
        logging.warning("Git tag push has been skipped due to config flag")


def actions_output(version):
    safe_version = version.replace("/", "-")

    logging.debug("Generated version is: %s", version)
    logging.debug("Safe version is: %s", safe_version)

    if os.getenv("GITHUB_OUTPUT"):
        with open(str(os.getenv("GITHUB_OUTPUT")), mode="a", encoding="utf-8") as env:
            print(f"version={version}", file=env)
            print(f"safe_version={safe_version}", file=env)


def get_config():
    logging.debug("Building config")

    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    log_level = os.environ.get("INPUT_LOG_LEVEL", "INFO")

    config = {
        "init_version": os.getenv("INPUT_INIT_VERSION"),
        "primary_branch": os.getenv("INPUT_PRIMARY_BRANCH"),
        "tag_prefix": {
            "candidate": os.getenv("INPUT_TAG_PREFIX_CANDIDATE", ""),
            "release": os.getenv("INPUT_TAG_PREFIX_RELEASE", "")
        },
        "git": {
            "name": "git-flow-action",
            "email": "git-flow-action@example.com"
        },
        "github": {
            "repository": os.getenv("GITHUB_REPOSITORY"),
            "url": os.getenv("INPUT_GITHUB_API_URL", "https://api.github.com"),
            "token": os.environ.get("INPUT_GITHUB_TOKEN")
        },
        "features": {
            "enable_git_push": os.getenv("INPUT_ENABLE_GIT_PUSH"),
            "enable_github_release": os.environ.get("INPUT_ENABLE_GITHUB_RELEASE")
        },
        "auto_release_branches": os.getenv("INPUT_AUTO_RELEASE_BRANCHES", "").split(","),
        "log_level": log_levels.get(log_level.lower(), logging.INFO),
        "keywords": {
            "patch_bump": ['[hotfix]', '[fix]', 'hotfix:', 'fix:'],
            "major_bump": ['[BUMP-MAJOR]', 'bump-major', 'feat!']
        }
    }

    #
    # This object exist only for debug logs
    #
    debug_config = copy.deepcopy(config)
    debug_config["github"]["token"] = "xxx-masked-xxx"

    logging.debug("Config has successfully built")
    logging.debug(debug_config)

    return config


def validate_config(config):
    logging.info("Config validation passed successfully.")


def create_github_release(config, tag):
    release_data = {
        "name": tag,
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "body": "",
        "generate_release_notes": False
    }

    logging.info(f"Creating GitHub release for {tag} tag")

    url = f"{config['github']['url']}/repos/{config['github']['repository']}/releases"
    headers = {
        "Authorization": f"Bearer {config['github']['token']}"
    }
    print(headers)
    res = requests.post(
        url, json=release_data, headers=headers, timeout=60
    )

    if not res:
        logging.error(f"Failed to create Github release for {tag} tag. Error: {res.text}")
        res.raise_for_status()


def get_bump_type(config, commit_message):
    result = 'minor'

    #
    # major
    #
    if any(keyword in commit_message for keyword in config["keywords"]["major_bump"]):
        result = 'major'

    #
    # patch
    #
    if any(keyword.lower() in commit_message.lower() for keyword in config["keywords"]["patch_bump"]):
        result = 'patch'

    logging.info(f"Based on the commit message '{commit_message}' '{result}' version bump is required")
    return result


def get_semver_version(config, git_tag=None):
    if git_tag is None:
        return semver.VersionInfo.parse(config["init_version"])

    #
    # Delete all leading letters and symbols except digits
    #
    git_tag_without_prefixes = re.sub(r'^[^\d]*', '', git_tag)

    return semver.VersionInfo.parse(git_tag_without_prefixes)


def get_new_semver_version(config, tag_last, bump_type):
    version = get_semver_version(config, tag_last)

    if bump_type == 'patch':
        return version.bump_patch()
    if bump_type == 'minor':
        return version.bump_minor()  # patch is reset automatically
    if bump_type == 'major':
        return version.bump_major()  # patch and minor are reset automatically


def create_release_branch(config, repo, new_version):
    branch_version = '.'.join(map(str, new_version[0:2]))
    branch_name = f"release/{branch_version}"

    try:
        repo.git.checkout('-b', branch_name)
        logging.info(f"Release branch {branch_name} successfully created")

        if config["features"]["enable_git_push"] == "true":
            repo.git.push('-u', 'origin', branch_name)
            logging.info(f"Release branch {branch_name} successfully pushed")
        else:
            logging.warning("Release branch push has been skipped due to config flag")
    except Exception as ex:
        logging.info(f"Failed to create release branch {branch_name}. Error: {ex}")


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    config = get_config()
    try:
        validate_config(config)
    except ValueError as ex:
        logging.error(f"Configuration validation failed: {ex}")

    logging.getLogger().setLevel(config["log_level"])

    repo_path = os.getcwd()
    repo = real_git.Repo(repo_path)

    #
    # Configure Git
    #
    repo.git.config('--global', 'user.email', config["git"]["email"])
    repo.git.config('--global', 'user.name', config["git"]["name"])

    # NOTE: it's available only for git v2.35.2+
    # DETAILS:
    #  https://github.com/actions/checkout/issues/766
    #  https://github.com/actions/checkout/issues/760
    gh_workspace = os.getenv("GITHUB_WORKSPACE")
    os.system(f"git config --global --add safe.directory {gh_workspace}")

    #
    # Get Git tag (for latest available)
    #
    try:
        tag_last = repo.git.describe('--tags', '--abbrev=0', '--candidates=100')
    except GitCommandError as ex:
        logging.warning("Not found any latest available Git tag")
        logging.debug(ex)
        tag_last = None

    #
    # Get Git tag (for HEAD)
    #
    try:
        tag_head = repo.git.describe("--exact-match", "--tags", "HEAD")
    except GitCommandError as ex:
        logging.warning("Not found Git tag for HEAD")
        logging.debug(ex)
        tag_head = None

    active_branch = str(repo.active_branch)
    commit_message = str(repo.head.reference.commit.message).rstrip('\n')

    logging.info("Gathering information ...")
    logging.info(f"Git branch: '{active_branch}'")
    logging.info(f"Git commit message: '{commit_message}'")
    logging.info(f"Git tag (HEAD): '{tag_head}'")
    logging.info(f"Git tag (latest available): '{tag_last}'")

    #
    # Check if new tag is not needed
    #
    if tag_head is not None:
        logging.warning(f"Git tag for HEAD has already exist: {tag_head}")
        actions_output(tag_head)
        return

    if active_branch == config["primary_branch"]:
        bump_type = get_bump_type(config, commit_message)

        #
        # Calculate new version (without any prefix)
        new_semver_version = get_new_semver_version(config, tag_last, bump_type)

        if (active_branch in config["auto_release_branches"]) or (
                '[RELEASE]' in commit_message and active_branch == config["primary_branch"]):

            new_tag = f"{config['tag_prefix']['release']}{str(new_semver_version)}"
            logging.info(f"New tag: {new_tag}")

            #
            # Push the tag
            git_create_and_push_tag(config, repo, new_tag)

            logging.info("Create new release")
            create_release_branch(config, repo, new_semver_version)

            #
            # Create GitHub release
            if config["features"]["enable_github_release"] == "true":
                create_github_release(config, new_tag)

            #
            # Switch back, and bump version in primary branch
            repo.git.checkout(active_branch)

            repo.git.commit('--allow-empty', '-m',
                            f"[git-flow-action] Bump upstream version tag up to {new_tag}")
            commit_sha = repo.head.commit.hexsha
            origin = repo.remote(name='origin')
            if config["features"]["enable_git_push"] == "true":
                origin.push()
                logging.info("Git branch has been pushed")
            else:
                logging.warning("Git branch push has been skipped due to config flag")

            new_semver_version_after_release = new_semver_version.bump_minor()
            if active_branch in config["auto_release_branches"]:
                new_tag = f"{config['tag_prefix']['release']}{str(new_semver_version_after_release)}"
            else:
                new_tag = f"{config['tag_prefix']['candidate']}{str(new_semver_version_after_release)}"

            logging.info(f"New tag for primary branch: {new_tag}")

            #
            # Push the tag (for primary branch)
            git_create_and_push_tag(config, repo, new_tag, commit_sha)

            #
            # Output
            actions_output(new_tag)
        else:
            new_tag = f"{config['tag_prefix']['candidate']}{str(new_semver_version)}"
            logging.info(f"New tag: {new_tag}")
            git_create_and_push_tag(config, repo, new_tag)

    if active_branch.startswith("release/"):
        #
        # Check that bump is not major
        bump_type = get_bump_type(config, commit_message)
        if bump_type == "major":
            logging.error("For release branches only minor or patch version bump is available")

        #
        # Calculate new version
        new_semver_version = get_new_semver_version(config, tag_last, bump_type)
        new_tag = f"{config['tag_prefix']['release']}{str(new_semver_version)}"
        logging.info(f"New tag: {new_tag}")

        #
        # Check release version and tag version
        tag_version_family = f"{new_semver_version[0]}.{new_semver_version[1]}"
        branch_version_family = active_branch.replace("release/", "")
        if tag_version_family != branch_version_family:
            logging.warning(
                f"Branch version family {branch_version_family} is not the same as Tag version family {tag_version_family}")

        #
        # Push the tag
        git_create_and_push_tag(config, repo, new_tag)

        #
        # Create GitHub release
        if config["features"]["enable_github_release"] == "true":
            create_github_release(config, new_tag)

        #
        # Output
        actions_output(new_tag)

    if active_branch != config["primary_branch"] and not active_branch.startswith("release/"):
        version = "sha/" + str(repo.head.object.hexsha[0:7])
        logging.info("Custom build version is: %s", version)
        logging.info("It is a build for custom branch (non %s or release). Tag won't be created",
                     config["primary_branch"])

        #
        # Output
        actions_output(version)


if __name__ == '__main__':
    sys.exit(main())
