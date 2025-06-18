# Git Flow Action

A GitHub Action that automates semantic versioning and release management following Git Flow principles. This action helps maintain a clean and consistent versioning strategy for your repositories.

## Features

- 🔄 **Automatic Version Bumping**: Automatically determines version bumps (major/minor/patch) based on commit messages
- 🏷️ **Tag Management**: Creates and manages Git tags with customizable prefixes
- 🌳 **Branch Management**: Supports Git Flow branching strategy with automatic release branch creation
- 📝 **Changelog Updates**: Automatically updates CHANGELOG.md with new versions
- 🚀 **GitHub Releases**: Creates GitHub releases for new versions
- 🔍 **Configurable Keywords**: Customize commit message keywords for version bumping
- 🔒 **Security**: Supports GitHub token authentication for secure operations

## Usage

### Basic Setup

```yaml
name: Git Flow

on:
  push:
    branches:
      - 'main'
      - 'release/**'

jobs:
  version:
    runs-on: ubuntu-24.04
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Git Flow
        id: set_version
        uses: kvendingoldo/git-flow-action@v2.0.2
        with:
          enable_github_release: true
          auto_release_branches: "main"
          tag_prefix_release: "v"
          github_token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Generated version
        run: echo ${{ steps.set_version.outputs.version }}
```

### Custom Tag Prefixes

```yaml
      - name: Git Flow
        uses: kvendingoldo/git-flow-action@v2.0.2
        with:
          init_version: "1.0.0"
          tag_prefix_release: "release-"
          tag_prefix_candidate: "candidate-"
```

### Configuration Options

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `init_version` | Initial version for new repositories | - | Yes |
| `primary_branch` | Name of the primary branch | `main` | No |
| `tag_prefix_release` | Prefix for release tags | `v` | No |
| `tag_prefix_candidate` | Prefix for release candidate tags | `rc/` | No |
| `enable_git_push` | Enable pushing to remote repository | `false` | No |
| `enable_github_release` | Enable creating GitHub releases | `false` | No |
| `auto_release_branches` | Comma-separated list of branches that trigger releases | - | No |
| `log_level` | Logging level (debug/info/warning/error/critical) | `info` | No |

### Version Bumping

The action automatically determines version bumps based on commit message keywords:

- **Major Version** (`[BUMP-MAJOR]`, `bump-major`, `feat!`)
- **Patch Version** (`[hotfix]`, `[fix]`, `hotfix:`, `fix:`)
- **Minor Version** (default for all other commits)

### Branch Strategy

- **Primary Branch** (e.g., `main`): Creates release candidates and handles version bumps
- **Release Branches** (`release/*`): Creates release versions and GitHub releases
- **Other Branches**: Creates custom build versions with commit SHA

## Outputs

The action provides the following outputs:

- `version`: The new version tag (e.g., `v1.0.0`)
- `safe_version`: A safe version string for use in filenames (e.g., `v1-0-0`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.


## Acknowledgments

- Inspired by Git Flow branching strategy
- Built with Python and GitHub Actions
- Uses semantic versioning (semver) for version management


<a href="https://star-history.com/#kvendingoldo/git-flow-action&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=kvendingoldo/git-flow-action&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=kvendingoldo/git-flow-action&type=Date" />
  </picture>
</a>

<!-- markdownlint-enable no-inline-html -->

<a id="licence"></a>
## LICENSE
The kvendingoldo/git-flow-action project is distributed under the Apache 2.0 license. See [LICENSE](LICENSE).
