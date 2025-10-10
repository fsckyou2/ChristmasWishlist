# Semantic Versioning Guide

This project follows [Semantic Versioning 2.0.0](https://semver.org/) with **automated version bumping**.

## Version Format

Versions are formatted as `MAJOR.MINOR.PATCH`:

- **MAJOR**: Incompatible API changes or major feature overhauls
- **MINOR**: New features added in a backwards-compatible manner
- **PATCH**: Backwards-compatible bug fixes

## Current Version

The current version is tracked in the `VERSION` file at the repository root.

You can also check the version in Python:

```python
from app import __version__
print(__version__)
```

## Automated Version Bumping (Main Workflow)

**This is the recommended workflow.** Versions are automatically bumped when you merge to the `main` branch.

### How It Works

1. **Develop on the `development` branch**
   ```bash
   git checkout development
   # Make your changes
   git add .
   git commit -m "feat: add new feature"
   git push
   ```

2. **Merge to `main`**
   ```bash
   git checkout main
   git merge development
   git push
   ```

3. **Automatic version bump happens**
   - GitHub Actions detects the push to main
   - Analyzes commit messages to determine bump type
   - Bumps the version in VERSION file
   - Updates CHANGELOG.md
   - Commits the changes with `[skip ci]`
   - Creates a git tag (e.g., `v1.1.0`)
   - Pushes tag to trigger Docker Hub deployment

### Commit Message Convention

The version bump type is determined by your commit messages using [Conventional Commits](https://www.conventionalcommits.org/):

- **MAJOR bump** (1.0.0 → 2.0.0):
  ```bash
  git commit -m "feat!: breaking change to API"
  # or
  git commit -m "BREAKING CHANGE: redesigned authentication"
  ```

- **MINOR bump** (1.0.0 → 1.1.0):
  ```bash
  git commit -m "feat: add CSV export feature"
  git commit -m "feat(wishlist): add filtering options"
  ```

- **PATCH bump** (1.0.0 → 1.0.1):
  ```bash
  git commit -m "fix: resolve email sending bug"
  git commit -m "docs: update README"
  git commit -m "chore: update dependencies"
  # Any commit that doesn't start with "feat:" or "BREAKING CHANGE:"
  ```

### Example Workflow

```bash
# On development branch
git checkout development

# Make multiple commits with conventional commit messages
git commit -m "fix: correct wishlist item validation"
git commit -m "feat: add email notifications for claims"
git commit -m "docs: update API documentation"

# Push to development
git push origin development

# Merge to main (this triggers auto version bump)
git checkout main
git merge development
git push origin main

# GitHub Actions will:
# 1. Detect "feat:" commits → bump MINOR version (e.g., 1.0.0 → 1.1.0)
# 2. Update VERSION file
# 3. Update CHANGELOG.md
# 4. Commit changes
# 5. Create tag v1.1.0
# 6. Push tag
# 7. Docker Hub deployment triggered by tag
```

## Manual Version Bumping (Alternative)

If you need to manually control the version bump:

### Using the Bump Script

```bash
# For bug fixes and minor changes
python scripts/bump_version.py patch

# For new features (backwards-compatible)
python scripts/bump_version.py minor

# For breaking changes or major releases
python scripts/bump_version.py major
```

The script will:
1. Update the `VERSION` file
2. Display the version change
3. Show git commands to commit and tag the release

### Manual Process

If you prefer to bump the version manually:

1. **Update VERSION file**
   ```bash
   echo "1.1.0" > VERSION
   ```

2. **Update CHANGELOG.md**
   - Move items from `[Unreleased]` to a new version section
   - Add the release date
   - Create a new empty `[Unreleased]` section

3. **Commit the version bump**
   ```bash
   git add VERSION CHANGELOG.md
   git commit -m "Bump version to 1.1.0"
   ```

4. **Create and push the git tag**
   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   ```

5. **Push the commit**
   ```bash
   git push
   ```

## Release Workflow

### Automated Workflow (When merging to main)

When you merge `development` to `main`, the following happens automatically:

1. **Push to main** detected
2. **Version Bump workflow** runs (completes fully before Docker build):
   - Analyzes commit messages
   - Determines bump type (major/minor/patch)
   - Updates VERSION file
   - Updates CHANGELOG.md
   - Commits changes with `[skip ci]`
   - Pushes commit
   - Creates git tag (e.g., `v1.2.3`)
   - Pushes tag
3. **Docker Hub deployment** triggered ONLY by the tag push:
   - Checks out code (VERSION is already updated)
   - Builds Docker image with correct version
   - Tags with multiple versions:
     - `v1.2.3` (exact version)
     - `v1.2` (major.minor)
     - `v1` (major only)
     - `latest` (most recent main)
   - Pushes to Docker Hub

**Important:** The Docker publish workflow is triggered ONLY by version tags (not by push to main). This ensures the VERSION file is always updated before the Docker image is built, preventing version mismatches.

### Manual Workflow (When manually tagging)

If you manually create and push a tag (e.g., `v1.2.3`):

1. **GitHub Actions** runs the CI/CD pipeline
2. **Docker Build** creates a new Docker image
3. **Docker Hub** receives the image with multiple tags:
   - `v1.2.3` (exact version)
   - `v1.2` (major.minor)
   - `v1` (major only)
   - `latest` (if on main branch)

## Version Bumping Examples

### Patch Release (Bug Fixes)

**Example**: Fix email sending bug

```bash
# Current version: 1.0.0
python scripts/bump_version.py patch
# New version: 1.0.1

git add VERSION
git commit -m "Bump version to 1.0.1"
git tag -a v1.0.1 -m "Fix email sending bug"
git push origin v1.0.1
git push
```

### Minor Release (New Features)

**Example**: Add export to CSV feature

```bash
# Current version: 1.0.1
python scripts/bump_version.py minor
# New version: 1.1.0

git add VERSION
git commit -m "Bump version to 1.1.0"
git tag -a v1.1.0 -m "Add CSV export feature"
git push origin v1.1.0
git push
```

### Major Release (Breaking Changes)

**Example**: Redesign API endpoints

```bash
# Current version: 1.1.0
python scripts/bump_version.py major
# New version: 2.0.0

git add VERSION
git commit -m "Bump version to 2.0.0"
git tag -a v2.0.0 -m "API redesign with breaking changes"
git push origin v2.0.0
git push
```

## Changelog Maintenance

Always update `CHANGELOG.md` when making changes:

### Adding Changes to Unreleased

As you work, add changes to the `[Unreleased]` section:

```markdown
## [Unreleased]

### Added
- New CSV export feature
- Search functionality in wishlist

### Fixed
- Email sending timeout issue
- URL scraping for Amazon

### Changed
- Improved mobile responsive design
```

### Creating a Release

When bumping the version, move unreleased changes to a new version section:

```markdown
## [Unreleased]

## [1.1.0] - 2025-01-15

### Added
- New CSV export feature
- Search functionality in wishlist

### Fixed
- Email sending timeout issue
```

## Pre-release Versions

For pre-release versions (alpha, beta, RC), use the format:

- `1.0.0-alpha.1`
- `1.0.0-beta.2`
- `1.0.0-rc.1`

Update VERSION file manually for pre-releases:

```bash
echo "1.0.0-beta.1" > VERSION
git add VERSION
git commit -m "Bump version to 1.0.0-beta.1"
git tag -a v1.0.0-beta.1 -m "Beta release 1"
git push origin v1.0.0-beta.1
git push
```

## Version in Application

The version is available in the Flask application:

```python
from app import __version__

@app.route('/version')
def version():
    return {'version': __version__}
```

## Best Practices

1. **Always update CHANGELOG.md** with every version bump
2. **Tag releases** with annotated tags (`git tag -a`)
3. **Write descriptive tag messages** explaining what's new
4. **Test thoroughly** before creating a release tag
5. **Use branches** for release preparation (optional):
   ```bash
   git checkout -b release-1.1.0
   # Make final tweaks, update changelog
   git commit -m "Prepare release 1.1.0"
   git checkout main
   git merge release-1.1.0
   git tag -a v1.1.0 -m "Release 1.1.0"
   ```

## Viewing Release History

```bash
# List all tags
git tag -l

# Show tag details
git show v1.0.0

# View changelog
cat CHANGELOG.md
```

## Docker Image Versions

After releasing, your Docker images will be available:

```bash
# Latest version
docker pull <username>/christmas-wishlist:latest

# Specific version
docker pull <username>/christmas-wishlist:v1.2.3

# Major version
docker pull <username>/christmas-wishlist:v1
```

## Troubleshooting

### Wrong version bumped
If you bumped the wrong version type, just run the script again:
```bash
python scripts/bump_version.py minor  # Oops, should be major
python scripts/bump_version.py major  # Correct it
```

### Tag already exists
If you need to recreate a tag:
```bash
git tag -d v1.0.0              # Delete local tag
git push origin :refs/tags/v1.0.0  # Delete remote tag
git tag -a v1.0.0 -m "Release 1.0.0"  # Recreate tag
git push origin v1.0.0         # Push new tag
```

### Forgot to update changelog
You can amend the commit:
```bash
# Edit CHANGELOG.md
git add CHANGELOG.md
git commit --amend --no-edit
git tag -d v1.0.0              # Delete tag
git tag -a v1.0.0 -m "Release 1.0.0"  # Recreate tag
git push --force-with-lease
git push origin v1.0.0
```
