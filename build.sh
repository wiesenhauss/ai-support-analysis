#!/bin/bash
# WordPress.com Support Analyzer - Simple Build Script
# Usage: ./build.sh [version]

echo "🔨 WordPress.com Support Analyzer - Build Tool"
echo "=============================================="

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if PyInstaller is available
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "❌ Error: PyInstaller is not installed"
    echo "💡 Run: pip install pyinstaller"
    exit 1
fi

# Run the build script
if [ -z "$1" ]; then
    echo "🚀 Building with auto-incremented version..."
    python3 build_executable.py
else
    echo "🚀 Building version $1..."
    python3 build_executable.py "$1"
fi

echo ""
echo "✅ Build process completed!"
echo "📁 Check the 'dist' folder for your executable" 