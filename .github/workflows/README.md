# GitHub Actions Workflows

This directory contains CI/CD workflows for the Christmas Wishlist project.

## Workflows

### 1. CI (`ci.yml`)

**Triggers**: Push or PR to `main`, `master`, or `development` branches

**Purpose**: Continuous integration testing

**Jobs**:
- **test**: Runs pytest on Python 3.11, 3.12, 3.13 with coverage reporting
- **lint**: Checks code formatting (Black) and quality (Flake8)
- **docker**: Verifies Docker build and container startup

**Usage**: Automatically runs on every push/PR. Ensures code quality before merging.

---

### 2. Auto Version Bump (`version-bump.yml`)

**Triggers**: Push to `main` branch (excluding VERSION and CHANGELOG.md changes)

**Purpose**: Automatically bump semantic version when development is merged to main

**How It Works**:
1. Detects push to main branch
2. Analyzes commit messages since last tag
3. Determines version bump type using Conventional Commits:
   - `BREAKING CHANGE:` or `feat!:` → MAJOR bump
   - `feat:` → MINOR bump
   - `fix:` or anything else → PATCH bump
4. Runs `scripts/bump_version.py` with determined type
5. Updates CHANGELOG.md with unreleased changes
6. Commits VERSION and CHANGELOG.md with `[skip ci]` flag
7. Creates git tag (e.g., `v1.2.3`)
8. Pushes tag to trigger Docker Hub deployment

**Requirements**:
- Commits should follow [Conventional Commits](https://www.conventionalcommits.org/) format
- Uses `GITHUB_TOKEN` for committing (automatically provided)
- Repository settings must allow GitHub Actions to create and push commits:
  - Go to Settings → Actions → General
  - Under "Workflow permissions", select "Read and write permissions"
  - Check "Allow GitHub Actions to create and approve pull requests" (optional)

**Prevents Infinite Loops**:
- Skips if commit message contains `[skip ci]`
- Ignores pushes that only change VERSION or CHANGELOG.md

**Example Commit Messages**:
```bash
feat: add CSV export feature          # → MINOR bump
fix: resolve email bug                # → PATCH bump
feat!: redesign API endpoints         # → MAJOR bump
BREAKING CHANGE: remove old API       # → MAJOR bump
docs: update README                   # → PATCH bump
```

---

### 3. Docker Hub Deployment (`docker-publish.yml`)

**Triggers**:
- Push of tags matching `v*.*.*` pattern ONLY
- Does NOT trigger on push to main (prevents race condition with version-bump)

**Purpose**: Build and push Docker images to Docker Hub

**Trigger Order**:
This workflow is triggered by tags created by the version-bump workflow, ensuring the VERSION file is always up-to-date before building the Docker image.

**How It Works**:
1. Checks out code
2. Sets up Docker Buildx
3. Logs into Docker Hub using secrets
4. Extracts metadata and tags:
   - `latest` - for main branch
   - `v1.2.3` - exact version from tag
   - `v1.2` - major.minor version
   - `v1` - major version only
   - `main-<sha>` - commit SHA for main branch
5. Builds Docker image with caching
6. Pushes to Docker Hub

**Requirements**:
- GitHub Secrets must be configured:
  - `DOCKERHUB_USERNAME` - Your Docker Hub username
  - `DOCKERHUB_TOKEN` - Docker Hub access token
- See `DOCKER_HUB_SETUP.md` for setup instructions

**Image Location**: `<username>/christmas-wishlist:latest`

---

## Workflow Sequence

### Typical Development Cycle

```
Development Branch
      ↓
  (commits with conventional commit messages)
      ↓
  git push origin development
      ↓
  [CI workflow runs] ✓
      ↓
Merge to Main
      ↓
  git push origin main
      ↓
  [CI workflow runs] ✓
      ↓
  [Version Bump workflow runs]
      ├── Analyzes commits
      ├── Bumps version (e.g., 1.0.0 → 1.1.0)
      ├── Updates VERSION file
      ├── Updates CHANGELOG.md
      ├── Commits changes with [skip ci]
      ├── Pushes commit
      └── Creates and pushes tag v1.1.0
      ↓
  [Docker Publish workflow TRIGGERED BY TAG]
      ├── Checks out code (with updated VERSION)
      ├── Builds Docker image with version 1.1.0
      ├── Tags: v1.1.0, v1.1, v1, latest
      └── Pushes to Docker Hub ✓
```

**Important:** The Docker publish workflow ONLY runs when a tag is created. This ensures:
1. VERSION file is already updated before building
2. No race condition between version-bump and docker-publish
3. Docker image always has the correct version

## Monitoring Workflows

1. Go to your GitHub repository
2. Click the "Actions" tab
3. View workflow runs and their status
4. Click on any run to see detailed logs

## Troubleshooting

### Version Bump Not Triggering

**Symptom**: Push to main doesn't create a new version

**Solutions**:
- Check that commit messages follow Conventional Commits format
- Verify the workflow file is in `.github/workflows/version-bump.yml`
- Check Actions tab for error messages
- Ensure push didn't contain `[skip ci]` in commit message

### Docker Push Fails

**Symptom**: Docker Hub deployment fails with authentication error

**Solutions**:
- Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are set
- Ensure Docker Hub token hasn't expired
- Check token has "Read, Write, Delete" permissions

### Infinite Loop Detected

**Symptom**: Version bump workflow keeps triggering itself

**Solutions**:
- The `[skip ci]` flag should prevent this
- Check `paths-ignore` in workflow is working
- Verify workflow only runs on pushes that change actual code

### CI Tests Failing

**Symptom**: CI workflow fails on test/lint job

**Solutions**:
- Run tests locally: `docker exec christmas-wishlist pytest`
- Check formatting: `docker exec christmas-wishlist black --check app/ tests/`
- Review error logs in GitHub Actions

## Disabling Workflows

To temporarily disable a workflow:

1. Go to repository Settings → Actions → General
2. Set "Actions permissions" to disable all, or:
3. Edit the workflow file and add `if: false` to the job:
   ```yaml
   jobs:
     build:
       if: false
       runs-on: ubuntu-latest
   ```

## Manual Workflow Triggers

Some workflows can be triggered manually:

1. Go to Actions tab
2. Select the workflow
3. Click "Run workflow" button
4. Choose branch and click "Run workflow"

Note: Current workflows don't support manual triggers (`workflow_dispatch`), but this can be added if needed.
