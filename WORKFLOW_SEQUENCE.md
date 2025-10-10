# Workflow Execution Sequence

This document explains the exact order of workflow execution when you merge to main.

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  DEVELOPMENT BRANCH                                             │
│  - Work on features                                             │
│  - Use conventional commits (feat:, fix:, etc.)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ git merge / git push
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  PUSH TO MAIN                                                   │
│  GitHub detects push event                                      │
└────────────────────────┬───────────────┬────────────────────────┘
                         │               │
                 ┌───────┘               └────────┐
                 │                                │
                 ↓                                ↓
    ┌────────────────────────┐       ┌──────────────────────┐
    │  CI WORKFLOW           │       │  VERSION-BUMP        │
    │  (.github/workflows/   │       │  (.github/workflows/ │
    │   ci.yml)              │       │   version-bump.yml)  │
    │                        │       │                      │
    │  ✓ Run tests           │       │  1. Analyze commits  │
    │  ✓ Check formatting    │       │  2. Bump VERSION     │
    │  ✓ Verify Docker build │       │  3. Update CHANGELOG │
    └────────────────────────┘       │  4. Commit changes   │
                                     │  5. Push commit      │
                                     │  6. CREATE TAG       │
                                     │  7. PUSH TAG         │
                                     └──────────┬───────────┘
                                                │
                                                │ Tag push triggers
                                                ↓
                                   ┌────────────────────────────┐
                                   │  DOCKER-PUBLISH            │
                                   │  (.github/workflows/       │
                                   │   docker-publish.yml)      │
                                   │                            │
                                   │  1. Checkout code          │
                                   │     (VERSION is updated!)  │
                                   │  2. Build Docker image     │
                                   │  3. Tag with versions      │
                                   │  4. Push to Docker Hub     │
                                   └────────────────────────────┘
```

## Step-by-Step Breakdown

### Step 1: Development Work
```bash
git checkout development
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git push origin development
```

**What happens:**
- CI workflow runs on development branch
- Tests and linting verify code quality

### Step 2: Merge to Main
```bash
git checkout main
git merge development
git push origin main
```

**What triggers:**
- ✅ CI workflow (runs tests, lint, docker build verification)
- ✅ Version-bump workflow (WAITS for completion)
- ❌ Docker-publish workflow (NOT triggered by push to main)

### Step 3: Version Bump Workflow Executes

**Execution order within workflow:**

1. **Checkout code** - Gets latest main branch
2. **Analyze commits** - Looks at commit messages since last tag
   - Finds: `feat:` → Determines MINOR bump
3. **Run bump script** - `python scripts/bump_version.py minor`
   - Updates VERSION: `1.0.0` → `1.1.0`
4. **Update CHANGELOG** - Moves unreleased changes to new version section
5. **Commit changes** - `git commit -m "chore: bump version to 1.1.0 [skip ci]"`
6. **Push commit** - `git push`
7. **Create tag** - `git tag -a v1.1.0 -m "Release version 1.1.0"`
8. **Push tag** - `git push origin v1.1.0`

**⏱️ Duration:** ~30-60 seconds

### Step 4: Docker Publish Workflow Triggers

**Triggered by:** Tag push from step 3.8

**Execution order:**

1. **Checkout code** - Gets code at tag `v1.1.0`
   - ✅ VERSION file contains `1.1.0`
   - ✅ CHANGELOG includes version 1.1.0
2. **Setup Docker Buildx** - Prepares Docker build environment
3. **Login to Docker Hub** - Authenticates with credentials
4. **Extract metadata** - Creates tags:
   - `v1.1.0` (exact version)
   - `v1.1` (major.minor)
   - `v1` (major)
   - `latest` (most recent)
5. **Build Docker image** - Builds from Dockerfile
   - Image includes VERSION file with `1.1.0`
6. **Push to Docker Hub** - Uploads all tags

**⏱️ Duration:** ~2-5 minutes (depending on image size and caching)

## Why This Order Matters

### ❌ **Problem if both triggered on push to main:**

```
Push to main
    ├─ Version-bump starts (updates VERSION to 1.1.0)
    └─ Docker-publish starts (reads VERSION = 1.0.0) ← WRONG!
```

Docker would build the image BEFORE version was updated, resulting in:
- Docker image tagged as v1.1.0
- But VERSION file inside image = 1.0.0 ❌

### ✅ **Solution with tag-only trigger:**

```
Push to main
    └─ Version-bump completes (updates VERSION, creates tag)
           └─ Tag triggers Docker-publish (reads VERSION = 1.1.0) ← CORRECT!
```

Docker builds the image AFTER version is updated, ensuring:
- Docker image tagged as v1.1.0
- VERSION file inside image = 1.1.0 ✅

## Monitoring the Sequence

When you push to main, watch the GitHub Actions tab:

```
Actions Tab View:

[Running]  CI                          Started 10s ago
[Running]  Auto Version Bump           Started 10s ago

           ↓ (CI completes in ~1 min)

[Success]  CI                          Completed
[Running]  Auto Version Bump           Running (analyzing commits...)

           ↓ (Version bump completes in ~30s)

[Success]  CI                          Completed
[Success]  Auto Version Bump           Completed (created tag v1.1.0)
[Running]  Build and Push Docker Image Started (triggered by v1.1.0)

           ↓ (Docker build takes ~3 min)

[Success]  CI                          Completed
[Success]  Auto Version Bump           Completed
[Success]  Build and Push Docker Image Completed
```

## Verification

After all workflows complete, verify the sequence worked:

1. **Check VERSION file on main branch:**
   ```bash
   git pull origin main
   cat VERSION
   # Should show: 1.1.0
   ```

2. **Check Docker Hub:**
   - Visit: https://hub.docker.com/r/YOUR_USERNAME/christmas-wishlist/tags
   - Should see: `v1.1.0`, `v1.1`, `v1`, `latest`

3. **Verify version in Docker image:**
   ```bash
   docker pull YOUR_USERNAME/christmas-wishlist:v1.1.0
   docker run --rm YOUR_USERNAME/christmas-wishlist:v1.1.0 cat VERSION
   # Should output: 1.1.0
   ```

## Troubleshooting

### Docker builds before version bump

**Symptom:** Docker image has old version in VERSION file

**Cause:** `docker-publish.yml` is triggering on push to main

**Fix:** Ensure `docker-publish.yml` only has tag trigger:
```yaml
on:
  push:
    tags:
      - 'v*.*.*'
  # NOT branches: [ main ]
```

### Docker never triggers

**Symptom:** Version bump completes but Docker workflow doesn't start

**Possible causes:**

1. **Using GITHUB_TOKEN instead of PAT** (most common)
   - GitHub's `GITHUB_TOKEN` cannot trigger other workflows
   - **Fix:** Use Personal Access Token (PAT) in version-bump.yml
   - See GITHUB_ACTIONS_SETUP.md Step 1 for PAT setup

2. **Tag wasn't pushed**
   - Check if tag exists: `git tag -l`
   - Verify tag pushed to remote: `git ls-remote --tags origin`

3. **Tag pattern doesn't match**
   - Check tag format matches `v*.*.*` (e.g., `v1.0.0` not `1.0.0`)

### Both workflows run simultaneously

**Symptom:** See both workflows starting at the same time

**Cause:** Docker-publish is triggered by both push and tag

**Fix:** Remove `branches: [ main ]` from docker-publish.yml

## Summary

**Key Points:**

1. ✅ Docker-publish ONLY triggers on tags
2. ✅ Version-bump creates the tag after updating VERSION
3. ✅ This guarantees VERSION is correct before Docker builds
4. ✅ Total time: ~3-6 minutes from push to Docker Hub
5. ✅ Fully automated, no manual intervention needed

**Remember:** Use conventional commit messages to control version bumping!
- `feat:` = minor version bump
- `fix:` = patch version bump
- `BREAKING CHANGE:` or `feat!:` = major version bump
