# 🚀 Git Flow Action

> Automate your Git Flow workflow with semantic versioning, automatic releases, and smart branch management

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/kvendingoldo/git-flow-action/pipeline.yaml?branch=main)](https://github.com/kvendingoldo/git-flow-action/actions)
[![Codecov](https://img.shields.io/codecov/c/github/kvendingoldo/git-flow-action)](https://codecov.io/gh/kvendingoldo/git-flow-action)
[![License](https://img.shields.io/github/license/kvendingoldo/git-flow-action)](LICENSE)

## ✨ Features

- 🔄 **Smart Semantic Versioning**: Automatically bumps versions based on commit messages
- 🏷️ **Flexible Tagging**: Support for both release and candidate tags with customizable prefixes
- 🌿 **Branch Management**: Automatic release branch creation and management
- 📝 **Commit Message Analysis**: Intelligent version bumping based on commit message keywords
- 🔧 **Configurable Workflow**: Customize behavior through environment variables
- 📦 **GitHub Release Integration**: Optional automatic GitHub release creation
- 🔒 **Security First**: Safe git operations with proper authentication

## 🎯 Use Cases

- **Continuous Delivery**: Automate version management in your CI/CD pipeline
- **Release Management**: Streamline the release process with automatic versioning
- **Branch Strategy**: Implement Git Flow with automated branch creation
- **Version Control**: Maintain consistent semantic versioning across your project

## 🚀 Quick Start

Add this action to your workflow:

```yaml
name: Version Management

on:
  push:
    branches:
      - main
      - 'release/**'

jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Git Flow Action
        uses: kvendingoldo/git-flow-action@v1
        with:
          init_version: "0.0.0"
          primary_branch: "main"
          tag_prefix_release: "v"
          tag_prefix_candidate: "rc/"
          enable_git_push: "true"
          enable_github_release: "true"
          auto_release_branches: "main"
```

## ⚙️ Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `init_version` | Initial version for new repositories | Required |
| `primary_branch` | Name of your primary branch | "main" |
| `tag_prefix_release` | Prefix for release tags | "" |
| `tag_prefix_candidate` | Prefix for candidate tags | "" |
| `enable_git_push` | Enable pushing tags and branches | "false" |
| `enable_github_release` | Create GitHub releases | "false" |
| `auto_release_branches` | Comma-separated list of branches for auto-release | "" |
| `log_level` | Logging level (debug, info, warning, error) | "info" |

## 📝 Commit Message Convention

The action automatically determines version bumps based on commit messages:

- **Major Version**: Use `[BUMP-MAJOR]`, `bump-major`, or `feat!` in commit message
- **Patch Version**: Use `[hotfix]`, `[fix]`, `hotfix:`, or `fix:` in commit message
- **Minor Version**: Default bump for other commit messages

## 🌿 Branch Strategy

- **Primary Branch**: Version bumps based on commit messages
- **Release Branches**: Only patch version bumps allowed
- **Feature Branches**: No version bumps, uses commit SHA

## 🔄 Workflow Example

1. **Feature Development**:
   ```bash
   git checkout -b feature/new-feature
   git commit -m "feat: add new feature"
   ```

2. **Release Creation**:
   ```bash
   git checkout main
   git commit -m "feat: new feature"
   # Action creates v1.0.0 tag and release/1.0 branch
   ```

3. **Hotfix**:
   ```bash
   git checkout release/1.0
   git commit -m "fix: critical bug"
   # Action creates v1.0.1 tag
   ```

## 📚 Examples

### Basic Setup
```yaml
- uses: kvendingoldo/git-flow-action@v1
  with:
    init_version: "1.0.0"
    enable_git_push: "true"
```

### Full Configuration
```yaml
- uses: kvendingoldo/git-flow-action@v1
  with:
    init_version: "0.0.0"
    primary_branch: "main"
    tag_prefix_release: "v"
    tag_prefix_candidate: "rc/"
    enable_git_push: "true"
    enable_github_release: "true"
    auto_release_branches: "main,develop"
    log_level: "debug"
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Support

If you find this action helpful, please give it a star! For issues and feature requests, please use the [GitHub issue tracker](https://github.com/kvendingoldo/git-flow-action/issues).
