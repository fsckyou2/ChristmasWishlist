# Docker Hub Deployment Setup

This document explains how to set up automated Docker image deployment to Docker Hub.

## Overview

When code is pushed to the `main` branch (e.g., when `development` is merged), a GitHub Actions workflow automatically:
1. Builds a Docker image using the Dockerfile
2. Tags the image appropriately
3. Pushes the image to Docker Hub

## Prerequisites

1. A Docker Hub account
2. A Docker Hub repository (or the workflow will create one automatically)
3. GitHub repository secrets configured

## Setting Up GitHub Secrets

The workflow requires two secrets to be configured in your GitHub repository:

### 1. Create a Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com/)
2. Click on your username in the top right corner
3. Select "Account Settings"
4. Go to "Security" → "Access Tokens"
5. Click "New Access Token"
6. Give it a description (e.g., "GitHub Actions - Christmas Wishlist")
7. Set permissions to "Read, Write, Delete"
8. Click "Generate"
9. **Copy the token immediately** (you won't be able to see it again)

### 2. Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add the following secrets:

   **DOCKERHUB_USERNAME**
   - Name: `DOCKERHUB_USERNAME`
   - Value: Your Docker Hub username (e.g., `johndoe`)

   **DOCKERHUB_TOKEN**
   - Name: `DOCKERHUB_TOKEN`
   - Value: The access token you generated in step 1

## Image Tagging Strategy

The workflow automatically tags images with:

- `latest` - The most recent build from the main branch
- `main-<commit-sha>` - Specific commit from main branch (e.g., `main-abc123f`)
- `v1.2.3` - Semantic version tags (if you tag a release with `v1.2.3`)
- `v1.2` - Major.minor version (if you tag a release)
- `v1` - Major version only (if you tag a release)

## Pulling the Image

Once deployed, you can pull the image from Docker Hub:

```bash
# Pull latest version
docker pull <your-username>/christmas-wishlist:latest

# Pull specific commit
docker pull <your-username>/christmas-wishlist:main-abc123f

# Pull specific version
docker pull <your-username>/christmas-wishlist:v1.2.3
```

## Running the Container

```bash
# Using docker run
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY="your-secret-key" \
  -e DATABASE_URL="sqlite:///wishlist.db" \
  --name christmas-wishlist \
  <your-username>/christmas-wishlist:latest

# Using docker compose (recommended)
# See docker-compose.yml for full configuration
docker compose up -d
```

## Workflow Triggers

The workflow runs when:
- Code is pushed to the `main` branch
- A tag matching `v*.*.*` is pushed (e.g., `v1.0.0`, `v2.1.3`)

## Monitoring Deployments

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "Build and Push Docker Image" workflow
4. View the progress and logs of each deployment

## Troubleshooting

### Authentication Failed
- Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are set correctly
- Ensure the access token hasn't expired
- Check that the token has "Read, Write, Delete" permissions

### Build Failed
- Check the GitHub Actions logs for specific error messages
- Verify the Dockerfile is valid
- Ensure all dependencies in requirements.txt are available

### Image Not Found on Docker Hub
- Verify the workflow completed successfully
- Check that you're using the correct username and image name
- Public repositories may take a few minutes to appear in search

## Creating a Release with Version Tag

To create a versioned release:

```bash
# Tag the commit
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push the tag
git push origin v1.0.0
```

This will trigger the workflow and create images tagged with `v1.0.0`, `v1.0`, `v1`, and `latest`.
