# GitHub Actions Setup Guide

This guide walks you through configuring GitHub Actions for automated testing, version bumping, and Docker Hub deployment.

## Prerequisites

- GitHub repository for your project
- Docker Hub account (for Docker deployment)
- Admin access to the repository

## Workflows Overview

This project uses two GitHub Actions workflows:

1. **CI Workflow** (`.github/workflows/ci.yml`)
   - Runs on: All pushes and pull requests
   - Purpose: Run tests, linting, and verify Docker build

2. **Release Workflow** (`.github/workflows/release.yml`)
   - Runs on: Push to main branch only
   - Purpose: Bump version → Build Docker image → Push to Docker Hub

## Step 1: Create Personal Access Token (PAT)

The release workflow needs a Personal Access Token to push version commits and tags.

### Create a Fine-Grained Personal Access Token

1. Go to GitHub → Click your profile picture → **Settings**
2. Scroll to **Developer settings** (bottom of left sidebar)
3. Click **Personal access tokens** → **Fine-grained tokens**
4. Click **Generate new token**
5. Configure the token:
   - **Name**: `ChristmasWishlist-Release`
   - **Expiration**: Choose expiration (90 days recommended, or custom)
   - **Repository access**: Select "Only select repositories"
     - Choose your `ChristmasWishlist` repository
   - **Permissions - Repository**:
     - Contents: **Read and write**
     - Metadata: **Read-only** (auto-selected)
6. Click **Generate token**
7. **Copy the token immediately** (you won't see it again!)

### Add PAT to GitHub Repository Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add secret:
   - Name: `PAT_TOKEN`
   - Value: The personal access token you just created
   - Click **Add secret**

**Why this is needed:**
The PAT allows the workflow to push version commits and tags to your repository.

## Step 2: Configure Docker Hub Secrets

The release workflow needs your Docker Hub credentials to push images.

### Create Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com/)
2. Click your username (top right) → **Account Settings**
3. Go to **Security** → **Access Tokens**
4. Click **New Access Token**
5. Name: `GitHub Actions - ChristmasWishlist`
6. Permissions: **Read, Write, Delete**
7. Click **Generate**
8. **Copy the token immediately** (you won't see it again!)

### Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these two secrets:

**Secret 1: DOCKERHUB_USERNAME**
- Name: `DOCKERHUB_USERNAME`
- Value: Your Docker Hub username (e.g., `johndoe`)
- Click **Add secret**

**Secret 2: DOCKERHUB_TOKEN**
- Name: `DOCKERHUB_TOKEN`
- Value: The access token you generated above
- Click **Add secret**

## Step 3: Verify Workflows are Enabled

1. Go to **Actions** tab in your repository
2. If you see a message about workflows being disabled:
   - Click **"I understand my workflows, go ahead and enable them"**
3. You should see the following workflows listed:
   - ✅ CI
   - ✅ Release

## Step 4: Test the Setup

### Test CI Workflow

Push any change to any branch:

```bash
git checkout development
echo "# test" >> README.md
git add README.md
git commit -m "test: verify CI workflow"
git push
```

1. Go to **Actions** tab
2. You should see "CI" workflow running
3. Wait for it to complete (green checkmark)

### Test Release Workflow

Merge to main to trigger version bump and Docker publish:

```bash
git checkout main
git merge development
git push
```

1. Go to **Actions** tab
2. You should see "Release" workflow running
3. It will:
   - Analyze your commit messages
   - Bump the version (patch/minor/major)
   - Update VERSION and CHANGELOG.md
   - Create and push a git tag
   - Build Docker image
   - Push to Docker Hub
4. Check that a new tag was created: **Code** → **Tags**
5. Verify on Docker Hub: https://hub.docker.com/r/YOUR_USERNAME/christmas-wishlist

## Commit Message Convention

The release workflow automatically determines version bump based on your commit messages:

- `feat:` or `feat(scope):` → **MINOR** version bump (1.0.0 → 1.1.0)
- `fix:` or other messages → **PATCH** version bump (1.0.0 → 1.0.1)
- `BREAKING CHANGE:` or `feat!:` → **MAJOR** version bump (1.0.0 → 2.0.0)

**Examples:**
```bash
git commit -m "feat: add dark mode toggle"           # Minor bump
git commit -m "fix: resolve login redirect issue"    # Patch bump
git commit -m "feat!: redesign authentication flow"  # Major bump
```

## Troubleshooting

### Release: 403 Permission Denied

**Error:**
```
remote: Permission to user/repo.git denied to github-actions[bot].
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
```

**Solution:**
1. Verify `PAT_TOKEN` secret is configured (Step 1)
2. Check PAT has "Contents: Read and write" permission
3. Ensure PAT hasn't expired
4. Try re-running the failed workflow

### Release Workflow Doesn't Trigger

**Possible causes:**
1. Commit message contains `[skip ci]`
2. Only VERSION, CHANGELOG.md, or documentation files were changed
3. Workflow is disabled in Actions settings

**Solution:**
- Make sure you're pushing actual code changes to main
- Check Actions tab to see if workflow is listed
- Review workflow YAML `paths-ignore` configuration

### Docker Push: Authentication Failed

**Error:**
```
Error: buildx failed with: ERROR: failed to solve: failed to push...
unauthorized: authentication required
```

**Solution:**
1. Verify secrets are set correctly (Step 2)
2. Check secret names match exactly: `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
3. Ensure Docker Hub token hasn't expired
4. Verify token has "Read, Write, Delete" permissions
5. Try regenerating the Docker Hub access token

### Docker Image Not Found on Docker Hub

**Check:**
1. Go to Actions tab and verify workflow completed successfully
2. Look for errors in the "Build and push Docker image" step
3. Verify Docker Hub username in secrets is correct
4. Check that the repository name matches: `christmas-wishlist`

### Version Didn't Bump

**Possible causes:**
1. No commits since last tag
2. Commit messages don't follow conventional format
3. Changes were only in ignored paths (docs, etc.)

**Solution:**
- Check commit messages: `git log --oneline`
- Ensure at least one commit follows conventional format
- Manually bump if needed: `python scripts/bump_version.py patch`

## Complete Checklist

Before pushing to main, ensure:

- [ ] Personal Access Token (PAT) created with Contents: Read and write permission
- [ ] GitHub secrets configured:
  - [ ] PAT_TOKEN
  - [ ] DOCKERHUB_USERNAME
  - [ ] DOCKERHUB_TOKEN
- [ ] Docker Hub access token created
- [ ] All workflows enabled in Actions tab
- [ ] CI workflow passes on development branch
- [ ] Commit messages follow Conventional Commits format
- [ ] Docker Hub repository ready to receive images

---

## Development Workflow

Once everything is set up correctly, your development workflow is:

```bash
# Normal development
git checkout development
git commit -m "feat: add cool feature"
git push
# → CI runs tests

# Release (merge to main)
git checkout main
git merge development
git push
# → Release workflow automatically:
#   ✓ Bumps version
#   ✓ Updates CHANGELOG
#   ✓ Creates tag
#   ✓ Builds Docker image
#   ✓ Pushes to Docker Hub
```

**Total time:** ~3-5 minutes from push to Docker Hub

Happy automating! 🚀
