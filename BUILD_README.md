# AI Support Analyzer - Build Guide

This guide explains how to build the AI Support Analyzer application into a standalone executable.

## 🚀 Quick Start

### Option 1: Quick Build (Recommended)
```bash
python3 compile.py
```
- ✅ **Automatic PyInstaller installation** if not present
- ✅ **Fast build process** without version management
- ✅ **Basic requirement checking**

### Option 2: Full Build with Version Management
```bash
python3 build_executable.py
```
- ✅ **Version tracking and increment options**
- ✅ **Comprehensive requirement checking**
- ✅ **Detailed build logging**
- ✅ **Automatic PyInstaller installation**

## 📋 Requirements

### System Requirements
- **Python 3.8+** (automatically checked)
- **macOS 10.15+** for macOS builds
- **~2GB free space** for build process

### Dependencies (Auto-Installed)
- **PyInstaller** - Automatically installed if missing
- **All Python packages** - Bundled in the executable

## 📦 Build Output

### macOS
- **Location**: `dist/AI Support Analyzer.app`
- **Type**: macOS Application Bundle
- **Size**: ~40-50 MB
- **Architecture**: Matches your system (Intel/Apple Silicon)

### Windows/Linux
- **Location**: `dist/AI_Support_Analyzer`
- **Type**: Standalone Executable
- **Size**: ~40-50 MB

## 🛠️ What Happens During Build

1. **Requirement Check**: Verifies Python version and dependencies
2. **PyInstaller Install**: Automatically installs if missing
3. **Dependency Analysis**: Scans for all required packages
4. **Bundle Creation**: Packages everything into standalone app
5. **Platform Optimization**: Creates platform-specific executable

## ✅ Features Included

- **Self-contained**: No Python installation required on target machines
- **All dependencies bundled**: OpenAI, pandas, matplotlib, etc.
- **Cross-platform**: Works on macOS, Windows, and Linux
- **Full GUI**: Complete tkinter interface included
- **All analysis scripts**: Every module packaged and ready

## 🚨 Troubleshooting

### Quick Diagnostics
Run the verification script to check your build environment:
```bash
python3 verify_build.py
```

### Critical Issue: Small Executable (10MB instead of 40MB)
This indicates missing dependencies and the app won't work:
```bash
# Clean and reinstall all dependencies
python3 -m pip uninstall -y -r requirements.txt
python3 -m pip install -r requirements.txt

# Clean previous build and rebuild
rm -rf build/ dist/
python3 build_executable.py
```

### "PyInstaller not found"
- **Solution**: The build script will offer to install it automatically
- **Manual fix**: `pip install pyinstaller`

### "Hidden import not found" warnings
These are usually okay, but if the executable is small or doesn't work:
```bash
# Use virtual environment for clean build
python3 -m venv ai_analyzer_env
source ai_analyzer_env/bin/activate
python3 -m pip install -r requirements.txt
python3 build_executable.py
```

### "Permission denied" on macOS
- **Solution**: Users need to right-click → "Open" to bypass Gatekeeper
- **Alternative**: Remove quarantine with `xattr -dr com.apple.quarantine "AI Support Analyzer.app"`

### App doesn't run on other machines
- Check architecture compatibility (M1/M2 vs Intel Mac)
- For broader compatibility, build on Intel Mac
- Size check: Should be 35-50MB, not 10MB

### Build process hangs or fails
```bash
# Nuclear option - clean everything
rm -rf build/ dist/ *.spec
python3 build_executable.py
```

### Size Guidelines
- **✅ Normal**: 35-50 MB (all dependencies bundled)
- **❌ Too small**: <30 MB (missing dependencies, won't work)
- **⚠️ Large**: >100 MB (usually okay, just lots of dependencies)

### Debug Mode
For detailed build information:
```bash
pyinstaller --debug=all --clean wordpress_support_analyzer.spec
```

## 📁 Project Structure

```
Local scripts - Next generation i2/
├── gui_app.py                          # Main GUI application
├── wordpress_support_analyzer.spec     # PyInstaller configuration
├── build_executable.py                 # Full build script
├── compile.py                          # Quick build script
├── custom-analysis.py                  # Custom analysis module
├── main-analysis-process.py            # Core analysis engine
├── [other analysis scripts...]
└── dist/
    └── AI Support Analyzer.app         # Built application
```

## 🎯 Distribution

The built application (`AI Support Analyzer.app`) is completely self-contained and can be:
- ✅ **Copied to other machines** (same architecture)
- ✅ **Distributed via file sharing**
- ✅ **Run without Python installation**
- ✅ **Used immediately** by end users

## 💡 Tips

- **First build**: May take 2-3 minutes
- **Subsequent builds**: Faster due to caching
- **Clean builds**: Use `--clean` flag (done automatically)
- **Version tracking**: Use `build_executable.py` for versioned releases

---

**Questions?** Reach out to @wiesenhauss in Slack! 🙋‍♂️ 