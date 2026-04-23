#!/bin/bash
# EagleTools — clean deploy script
# Usage: bash deploy.sh
set -e

echo "🔄 Pulling latest code from main..."
git fetch origin
git reset --hard origin/main
echo "✅ Code: $(git log --oneline -1)"

echo ""
echo "🐳 Rebuilding Docker images (no cache)..."
docker compose build --no-cache

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "✅ Done. Container status:"
docker compose ps
