#!/bin/bash
# Setup FFmpeg environment for Heroku

echo "🔧 Setting up FFmpeg environment..."

# Add common FFmpeg installation paths to PATH
export PATH="/app/.apt/usr/bin:$PATH"
export PATH="/usr/bin:$PATH"

# Check if ffmpeg and ffprobe are available
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ ffmpeg found: $(which ffmpeg)"
    ffmpeg_version=$(ffmpeg -version 2>&1 | head -n1)
    echo "   Version: $ffmpeg_version"
else
    echo "❌ ffmpeg not found in PATH"
fi

if command -v ffprobe >/dev/null 2>&1; then
    echo "✅ ffprobe found: $(which ffprobe)"
else
    echo "❌ ffprobe not found in PATH"
fi

# Set FFmpeg path for pytgcalls
export FFMPEG_BINARY=$(which ffmpeg 2>/dev/null || echo "ffmpeg")
export FFPROBE_BINARY=$(which ffprobe 2>/dev/null || echo "ffprobe")

echo "🎵 FFmpeg environment setup complete"
