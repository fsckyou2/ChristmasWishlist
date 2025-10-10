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
    ┌────────────────────────┐       ┌──────────────────────────┐
    │  CI WORKFLOW           │       │  RELEASE WORKFLOW        │
    │  (.github/workflows/   │       │  (.github/workflows/     │
    │   ci.yml)              │       │   release.yml)           │
    │                        │       │                          │
    │  ✓ Run tests           │       │  All in one workflow:    │
    │  ✓ Check formatting    │       │                          │
    │  ✓ Verify Docker build │       │  1. Analyze commits      │
    └────────────────────────┘       │  2. Bump VERSION         │
                                     │  3. Update CHANGELOG     │
                                     │  4. Commit changes       │
                                     │  5. Push commit          │
                                     │  6. Create tag           │
                                     │  7. Push tag             │
                                     │  8. Build Docker image   │
                                     │  9. Push to Docker Hub   │
                                     └──────────────────────────┘
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
- ✅ Release workflow (version bump + Docker publish)

Both run in parallel and independently.

### Step 3: Release Workflow Executes

**Single workflow with all steps:**

1. **Checkout code** - Gets latest main branch
2. **Analyze commits** - Looks at commit messages since last tag
   - Finds: `feat:` → Determines MINOR bump
3. **Bump version** - `python scripts/bump_version.py minor`
   - Updates VERSION: `1.0.0` → `1.1.0`
4. **Update CHANGELOG** - Moves unreleased changes to new version section
5. **Commit changes** - `git commit -m "chore: bump version to 1.1.0 [skip ci]"`
6. **Push commit** - `git push`
7. **Create tag** - `git tag -a v1.1.0 -m "Release version 1.1.0"`
8. **Push tag** - `git push origin v1.1.0`
9. **Build Docker image** - Builds from Dockerfile with updated VERSION
10. **Push to Docker Hub** - Uploads with tags: `v1.1.0`, `v1.1`, `v1`, `latest`

**⏱️ Duration:** ~3-5 minutes total

## Why This Approach?

### Single Workflow = Guaranteed Order

All steps run in sequence within one workflow, ensuring:
- ✅ VERSION file is updated before Docker build
- ✅ Tag is created after version is committed
- ✅ Docker image contains the correct version
- ✅ No race conditions or timing issues

### Commit Message Driven

Version bumping is automatic based on conventional commits:
- `feat:` → Minor bump (1.0.0 → 1.1.0)
- `fix:` → Patch bump (1.0.0 → 1.0.1)
- `feat!:` or `BREAKING CHANGE:` → Major bump (1.0.0 → 2.0.0)

## Monitoring the Sequence

When you push to main, watch the GitHub Actions tab:

```
Actions Tab View:

[Running]  CI                          Started 10s ago
[Running]  Release                     Started 10s ago

           ↓ (CI completes in ~1 min)

[Success]  CI                          Completed
[Running]  Release                     Running (bumping version...)

           ↓ (Release completes in ~3-5 min)

[Success]  CI                          Completed
[Success]  Release                     Completed (v1.1.0 pushed to Docker Hub)
```

## Verification

After the release workflow completes, verify it worked:

1. **Check VERSION file on main branch:**
   ```bash
   git pull origin main
   cat VERSION
   # Should show: 1.1.0
   ```

2. **Check tags:**
   ```bash
   git tag -l
   # Should include: v1.1.0
   ```

3. **Check Docker Hub:**
   - Visit: https://hub.docker.com/r/YOUR_USERNAME/christmas-wishlist/tags
   - Should see: `v1.1.0`, `v1.1`, `v1`, `latest`

4. **Verify version in Docker image:**
   ```bash
   docker pull YOUR_USERNAME/christmas-wishlist:v1.1.0
   docker run --rm YOUR_USERNAME/christmas-wishlist:v1.1.0 cat VERSION
   # Should output: 1.1.0
   ```

## Troubleshooting

### Release workflow doesn't trigger

**Symptom:** Push to main but no Release workflow

**Possible causes:**
1. Commit message contains `[skip ci]`
2. Only changed ignored files (`.md`, `.github/**`, `VERSION`, `CHANGELOG.md`)
3. Workflow is disabled

**Fix:**
- Push actual code changes
- Check Actions tab to see if workflow is listed
- Verify workflow is enabled

### Version didn't bump

**Symptom:** Release ran but version stayed the same

**Possible causes:**
1. No commits since last tag
2. All commits are merge commits without conventional format

**Fix:**
- Check commit messages: `git log --oneline`
- Ensure at least one commit uses `feat:`, `fix:`, etc.

### Docker image has wrong version

**Symptom:** Docker tag is v1.1.0 but VERSION file inside shows 1.0.0

**This shouldn't happen** with the single workflow approach, but if it does:
- Check that workflow completed all steps successfully
- Verify VERSION file was committed before Docker build step
- Look for errors in workflow logs

### PAT authentication failed

**Symptom:** `403 Permission denied` when pushing

**Fix:**
1. Verify `PAT_TOKEN` secret exists in repository
2. Check PAT has "Contents: Read and write" permission
3. Ensure PAT hasn't expired
4. Regenerate PAT if needed

## Summary

**Key Points:**

1. ✅ Single workflow combines version bump + Docker publish
2. ✅ All steps run in sequence, no race conditions
3. ✅ Commit messages control version bumping automatically
4. ✅ Total time: ~3-5 minutes from push to Docker Hub
5. ✅ Fully automated, no manual intervention needed

**Remember:** Use conventional commit messages!
- `feat:` = minor version bump
- `fix:` = patch version bump
- `BREAKING CHANGE:` or `feat!:` = major version bump
