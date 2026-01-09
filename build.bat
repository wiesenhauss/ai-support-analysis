@echo off
REM WordPress.com Support Analyzer - Windows Build Script
REM Usage: build.bat [version]

echo 🔨 WordPress.com Support Analyzer - Build Tool
echo ==============================================

REM Check if python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if PyInstaller is available
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: PyInstaller is not installed
    echo 💡 Run: pip install pyinstaller
    pause
    exit /b 1
)

REM Run the build script
if "%1"=="" (
    echo 🚀 Building with auto-incremented version...
    python build_executable.py
) else (
    echo 🚀 Building version %1...
    python build_executable.py %1
)

echo.
echo ✅ Build process completed!
echo 📁 Check the 'dist' folder for your executable
pause 