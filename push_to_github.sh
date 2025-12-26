#!/bin/bash
# Script to push to GitHub repository

echo "Setting up GitHub repository..."

# Configure git user (if not already set)
git config user.name "Steven Callens" 2>/dev/null || true
git config user.email "stevencallens@users.noreply.github.com" 2>/dev/null || true

# Add remote
echo "Adding GitHub remote..."
git remote add origin https://github.com/scalle0/document-search-system.git 2>/dev/null || echo "Remote already exists"

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Done! Your repository is now at:"
echo "   https://github.com/scalle0/document-search-system"
echo ""
echo "Note: You may need to authenticate with GitHub."
echo "If prompted, use your GitHub personal access token as the password."
