# Manual Docker Cleanup Guide

Since Docker is unresponsive due to full storage, here are manual cleanup options:

## Option 1: Clean via Docker Desktop (Recommended)

1. **Open Docker Desktop**
2. **Go to Settings** (gear icon)
3. **Navigate to "Resources" → "Advanced"**
4. **Click "Clean / Purge data"** or **"Remove all data"**
   - This will remove all Docker images, containers, and volumes
   - ⚠️ **Warning**: This removes ALL Docker data, not just SWE-bench

## Option 2: Clean via Docker Desktop Disk Image

On macOS, Docker Desktop stores data in a disk image:

1. **Quit Docker Desktop completely**
   - Right-click Docker icon in menu bar → Quit Docker Desktop
   - Or: `killall Docker`

2. **Find and resize Docker's disk image**:
   ```bash
   # Docker Desktop typically stores data at:
   ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
   
   # Check its size:
   ls -lh ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
   ```

3. **In Docker Desktop Settings**:
   - Go to Settings → Resources → Advanced
   - Reduce the disk image size (this will trigger cleanup)
   - Or delete the disk image entirely (Docker will recreate it)

## Option 3: Nuclear Option - Remove All Docker Data

If you want to completely reset Docker:

```bash
# 1. Quit Docker Desktop
killall Docker

# 2. Remove Docker data (⚠️ removes EVERYTHING)
rm -rf ~/Library/Containers/com.docker.docker
rm -rf ~/.docker

# 3. Restart Docker Desktop
open -a Docker
```

## Option 4: Try Docker Commands with Patience

If you want to try removing images one by one (very slow):

```bash
# List all images (this may take minutes)
docker images

# Remove specific images by ID (replace IMAGE_ID)
docker rmi -f IMAGE_ID

# Or try to remove all unused images
docker image prune -a -f

# Remove all stopped containers
docker container prune -f

# Remove all unused data
docker system prune -a -f
```

## Option 5: Use the Python Script (if Docker becomes responsive)

Once Docker is working again:

```bash
# Activate virtual environment if needed
source .venv/bin/activate

# Remove all SWE-bench images
python clear_cache.py --cache_level all --yes --timeout 30
```

## Recommended Approach

1. **First**: Try Option 1 (Docker Desktop GUI cleanup)
2. **If that doesn't work**: Try Option 2 (resize disk image)
3. **Last resort**: Option 3 (complete reset)

After cleanup, restart Docker Desktop and verify:
```bash
docker system df
```

