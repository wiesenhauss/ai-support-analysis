# WordPress.com Support Analyzer - Build Instructions

## Overview

This document explains how to build standalone executable files from the WordPress.com Support Analyzer Python scripts using PyInstaller. The build system creates a single executable file that users can run without having Python installed.

## Quick Start

### Option 1: Simple Python Compile Script (Recommended)

```bash
python3 compile.py           # Auto-increment version
python3 compile.py 1.2.0     # Specific version  
python3 compile.py --help    # Show help
```

This is the **easiest and most reliable way** to build. The script checks requirements, runs the build, and provides clear feedback.

### Option 2: Advanced Python Build Script

```bash
python3 build_executable.py              # Auto-increment version
python3 build_executable.py 1.2.0        # Specific version
python3 build_executable.py --clean      # Clean build artifacts only
```

### Option 3: Platform-Specific Scripts

**On macOS/Linux:**
```bash
./build.sh                # Auto-increment version
./build.sh 1.2.0         # Specific version
```

**On Windows:**
```cmd
build.bat                 # Auto-increment version
build.bat 1.2.0          # Specific version
```

### Option 4: Manual PyInstaller

```bash
pyinstaller --clean wordpress_support_analyzer.spec
```

## Prerequisites

1. **Python 3.7+** installed and in PATH
2. **PyInstaller** installed: `pip install pyinstaller`
3. **All dependencies** installed: `pip install -r requirements.txt`

## Build Process

The build system:

1. **Cleans** previous build artifacts (`build/`, `dist/`, `.pyc` files)
2. **Updates** the PyInstaller spec file with version information
3. **Compiles** all Python scripts into a single executable using PyInstaller
4. **Creates** distribution files (README, version info)
5. **Reports** build success and file locations

## Build Output

After a successful build, you'll find:

```
dist/
└── WordPress_Support_Analyzer_v1.0.0    # The executable file (macOS/Linux)
└── WordPress_Support_Analyzer_v1.0.0.exe # The executable file (Windows)

README_Distribution.txt                   # User instructions
version.json                             # Version tracking
env_template.txt                         # Environment setup template
```

## Version Management

### Automatic Versioning
- Running without a version number auto-increments the patch version
- Version info is stored in `version.json`
- Build numbers are tracked automatically

### Manual Versioning
- Specify any semantic version: `1.0.0`, `2.1.3`, `1.0.0-beta`
- Version becomes part of the executable filename

### Version File (`version.json`)
```json
{
  "version": "1.0.0",
  "build_number": 1,
  "last_build": "2024-01-15T10:30:00"
}
```

## Distribution

### For End Users
Distribute these files to users:
1. **`WordPress_Support_Analyzer_vX.X.X`** - The main executable
2. **`README_Distribution.txt`** - Usage instructions
3. **`env_template.txt`** - Environment setup template

### User Setup
Users need to:
1. Download the executable
2. Create a `.env` file with their OpenAI API key:
   ```
   OPENAI_API_KEY=sk-proj-your_api_key_here
   ```
3. Run the executable

## Usage Examples

### End User Commands

**Interactive Mode:**
```bash
./WordPress_Support_Analyzer_v1.0.0
```

**Command Line Mode:**
```bash
./WordPress_Support_Analyzer_v1.0.0 -file="data.csv"
./WordPress_Support_Analyzer_v1.0.0 -file="data.csv" -limit=1000
```

## Build Troubleshooting

### Common Issues

**Python not found:**
- Ensure Python 3.7+ is installed and in PATH
- On macOS: `brew install python3`
- On Windows: Download from python.org

**PyInstaller not found:**
```bash
pip install pyinstaller
```

**Missing dependencies:**
```bash
pip install -r requirements.txt
```

**Permission denied (macOS/Linux):**
```bash
chmod +x build.sh
chmod +x dist/WordPress_Support_Analyzer_v1.0.0
```

**Large executable size:**
- Normal for PyInstaller (30-50 MB)
- Includes Python runtime and all dependencies
- Use UPX compression (already enabled) to reduce size

### Clean Build
If you encounter issues:
```bash
python3 build_executable.py --clean
python3 build_executable.py 1.0.0
```

## Development Workflow

### Regular Updates
1. Make changes to Python scripts
2. Test changes: `python3 orchestrator.py -file="test_data.csv"`
3. Build new version: `python3 compile.py 1.0.1`
4. Test executable: `./dist/WordPress_Support_Analyzer_v1.0.1 -file="test_data.csv"`
5. Distribute to users

### Version Strategy
- **Patch (1.0.X)** - Bug fixes, small improvements
- **Minor (1.X.0)** - New features, significant improvements
- **Major (X.0.0)** - Breaking changes, major overhauls

## Build Script Features

### Automated Features
- ✅ Dependency verification
- ✅ Automatic cleanup
- ✅ Version management
- ✅ Cross-platform support
- ✅ Error handling
- ✅ Progress reporting
- ✅ File size reporting
- ✅ Distribution file creation

### Build Options
- Auto-increment versioning
- Manual version specification
- Clean-only mode
- Detailed error reporting

## Technical Details

### PyInstaller Configuration
- **Mode:** One-file executable
- **Console:** Enabled (for logging and interaction)
- **UPX:** Enabled (compression)
- **Hidden imports:** All required modules specified
- **Data files:** All Python scripts included

### File Structure in Executable
```
WordPress_Support_Analyzer_v1.0.0
├── orchestrator.py (main entry point)
├── main-analysis-process.py
├── support-data-cleanup.py
├── support-data-precleanup.py
├── predict_csat.py
├── topic-aggregator.py
├── csat-trends.py
├── product-feedback-trends.py
├── goals-trends.py
├── aggregate-daily-reports.py
├── visualize-overall-sentiment.py
└── [Python runtime + dependencies]
```

## Support

For build issues:
1. Check this documentation
2. Verify prerequisites
3. Try a clean build
4. Check PyInstaller documentation
5. Contact the development team

---
*Generated by WordPress.com Support Analysis Pipeline* 