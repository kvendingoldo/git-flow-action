import os
import sys
import pytest
import logging
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    # Set test environment variables
    os.environ["INPUT_INIT_VERSION"] = "0.0.0"
    os.environ["INPUT_PRIMARY_BRANCH"] = "main"
    os.environ["INPUT_TAG_PREFIX_CANDIDATE"] = "rc/"
    os.environ["INPUT_TAG_PREFIX_RELEASE"] = ""
    os.environ["INPUT_ENABLE_GIT_PUSH"] = "true"
    os.environ["INPUT_ENABLE_GITHUB_RELEASE"] = "true"
    os.environ["INPUT_ENABLE_CUSTOM_BRANCH"] = "true"
    os.environ["INPUT_AUTO_RELEASE_BRANCHES"] = "main"
    os.environ["INPUT_LOG_LEVEL"] = "DEBUG"

    # Setup logging for tests
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    yield

    # Cleanup
    for key in [
        "INPUT_INIT_VERSION",
        "INPUT_PRIMARY_BRANCH",
        "INPUT_TAG_PREFIX_CANDIDATE",
        "INPUT_TAG_PREFIX_RELEASE",
        "INPUT_ENABLE_GIT_PUSH",
        "INPUT_ENABLE_GITHUB_RELEASE",
        "INPUT_ENABLE_CUSTOM_BRANCH",
        "INPUT_AUTO_RELEASE_BRANCHES",
        "INPUT_LOG_LEVEL"
    ]:
        if key in os.environ:
            del os.environ[key]
