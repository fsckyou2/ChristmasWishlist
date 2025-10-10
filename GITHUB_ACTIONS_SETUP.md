# GitHub Actions Setup Guide

This guide walks you through configuring GitHub Actions for automated version bumping and Docker Hub deployment.

## Prerequisites

- GitHub repository for your project
- Docker Hub account (for Docker deployment)
- Admin access to the repository

## Step 1: Configure Repository Permissions

The automated version bump workflow needs permission to commit and push to your repository.

### Enable Write Permissions for GitHub Actions

1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. In the left sidebar, click **Actions** → **General**
4. Scroll to **Workflow permissions**
5. Select **"Read and write permissions"**
6. (Optional) Check **"Allow GitHub Actions to create and approve pull requests"**
7. Click **Save**

**Screenshot reference:**
```
Workflow permissions
● Read repository contents and packages permissions
○ Read and write permissions   ← SELECT THIS

□ Allow GitHub Actions to create and approve pull requests   ← OPTIONAL
```

**Why this is needed:**
The version bump workflow commits VERSION and CHANGELOG.md changes back to the repository. Without write permissions, you'll get a 403 error when the workflow tries to push.

## Step 2: Configure Docker Hub Secrets

The Docker Hub deployment workflow needs your Docker Hub credentials.

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
- Value: The access token you generated in step 1
- Click **Add secret**

## Step 3: Verify Workflows are Enabled

1. Go to **Actions** tab in your repository
2. If you see a message about workflows being disabled:
   - Click **"I understand my workflows, go ahead and enable them"**
3. You should see the following workflows listed:
   - ✅ CI
   - ✅ Auto Version Bump
   - ✅ Build and Push Docker Image

## Step 4: Test the Setup

### Test CI Workflow

```bash
# Make any change to code
git checkout development
echo "# test" >> README.md
git add README.md
git commit -m "test: verify CI workflow"
git push
```

1. Go to **Actions** tab
2. You should see "CI" workflow running
3. Wait for it to complete (green checkmark)

### Test Version Bump Workflow

```bash
# Merge to main
git checkout main
git merge development
git push
```

1. Go to **Actions** tab
2. You should see "Auto Version Bump" workflow running
3. It should:
   - Commit version changes
   - Create a git tag
   - Trigger Docker Hub deployment
4. Check that a new tag was created: **Code** → **Tags**

### Test Docker Hub Deployment

1. After version bump completes, "Build and Push Docker Image" should run
2. Check **Actions** tab for the workflow
3. Once complete, verify on Docker Hub:
   - Go to https://hub.docker.com/r/YOUR_USERNAME/christmas-wishlist
   - You should see new tags (latest, v1.x.x, etc.)

## Troubleshooting

### Version Bump: 403 Permission Denied

**Error:**
```
remote: Permission to user/repo.git denied to github-actions[bot].
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
```

**Solution:**
1. Check Step 1 above - ensure "Read and write permissions" is enabled
2. Verify the workflow has `permissions: contents: write` in the YAML
3. Try re-running the failed workflow

### Version Bump: Workflow Doesn't Trigger

**Possible causes:**
1. Commit message contains `[skip ci]`
2. Only VERSION or CHANGELOG.md was changed
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
1. Verify secrets are set correctly (Step 2 above)
2. Check secret names match exactly: `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
3. Ensure Docker Hub token hasn't expired
4. Verify token has "Read, Write, Delete" permissions
5. Try regenerating the Docker Hub access token

### Docker Push: Image Not Found on Docker Hub

**Check:**
1. Go to Actions tab and verify workflow completed successfully
2. Look for any errors in the "Build and push Docker image" step
3. Verify Docker Hub username in secrets is correct
4. Check that the repository name matches: `christmas-wishlist`

### Workflow Infinite Loop

**Symptom:** Version bump keeps triggering itself

**This should NOT happen if configured correctly:**
- The workflow has `if: "!contains(github.event.head_commit.message, '[skip ci]')"`
- Commits use `[skip ci]` flag
- `paths-ignore` prevents triggering on VERSION/CHANGELOG changes

**If it happens:**
1. Disable the workflow temporarily: Settings → Actions → Disable workflow
2. Check the commit messages in the loop
3. Verify `[skip ci]` is in the commit message
4. Re-enable workflow after investigation

## Advanced Configuration

### Change Branch for Auto Version Bump

Edit `.github/workflows/version-bump.yml`:

```yaml
on:
  push:
    branches:
      - production  # Change from 'main'
```

### Disable Specific Workflows

Create a file `.github/workflows/disabled/` and move workflows you want to disable:

```bash
mkdir -p .github/workflows/disabled
mv .github/workflows/version-bump.yml .github/workflows/disabled/
```

### Manual Workflow Trigger

Add `workflow_dispatch` to any workflow to enable manual triggering:

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:  # Add this
```

Then you can run it manually from Actions tab → Select workflow → Run workflow

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Rotate Docker Hub tokens** periodically (every 6-12 months)
3. **Use least privilege** - only grant permissions that are needed
4. **Review workflow runs** regularly in the Actions tab
5. **Enable branch protection** on main branch (Settings → Branches)

## Getting Help

If you encounter issues not covered here:

1. **Check workflow logs:**
   - Actions tab → Click on failed run → Click on failed job
   - Review detailed logs for error messages

2. **Review workflow files:**
   - `.github/workflows/ci.yml`
   - `.github/workflows/version-bump.yml`
   - `.github/workflows/docker-publish.yml`

3. **Verify configuration:**
   - Repository settings (permissions, secrets)
   - Workflow YAML syntax
   - Git configuration

4. **Test locally:**
   - Run pytest locally
   - Test Docker build locally
   - Manually run version bump script

## Complete Checklist

Before pushing to main, ensure:

- [ ] Repository permissions: "Read and write permissions" enabled
- [ ] Docker Hub access token created
- [ ] GitHub secrets configured: DOCKERHUB_USERNAME, DOCKERHUB_TOKEN
- [ ] All workflows enabled in Actions tab
- [ ] CI workflow passes on development branch
- [ ] Commit messages follow Conventional Commits format
- [ ] Version bump tested on a test branch first (optional)
- [ ] Docker Hub repository ready to receive images

---

Once everything is set up correctly, your development workflow becomes:

```bash
# Normal development
git checkout development
git commit -m "feat: add cool feature"
git push

# Release (merge to main)
git checkout main
git merge development
git push

# GitHub Actions automatically:
# ✓ Runs tests
# ✓ Bumps version
# ✓ Creates tag
# ✓ Builds Docker image
# ✓ Pushes to Docker Hub
```

Happy automating! 🚀
