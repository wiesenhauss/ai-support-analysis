#!/usr/bin/env python3
"""
Build Verification Script for AI Support Analyzer
Helps troubleshoot build issues and validate dependencies

Usage: python3 verify_build.py
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Verify Python version compatibility."""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major != 3:
        print(f"❌ Python {version.major}.{version.minor} - Need Python 3.x")
        return False
    elif version.minor < 8:
        print(f"⚠️  Python {version.major}.{version.minor} - Recommended Python 3.8+")
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    
    return True

def check_required_files():
    """Check if all required project files exist."""
    print("\n📁 Checking project files...")
    
    required_files = [
        'gui_app.py',
        'orchestrator.py',
        'main-analysis-process.py',
        'support-data-precleanup.py',
        'support-data-cleanup.py',
        'predict_csat.py',
        'topic-aggregator.py',
        'csat-trends.py',
        'product-feedback-trends.py',
        'goals-trends.py',
        'custom-analysis.py',
        'aggregate-daily-reports.py',
        'visualize-overall-sentiment.py',
        'talktodata.py',
        'wordpress_support_analyzer.spec',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Warning: {len(missing_files)} files missing!")
        return False
    
    return True

def check_dependencies():
    """Check if all required Python packages are installed."""
    print("\n📦 Checking Python dependencies...")
    
    # Core dependencies with their import names
    dependencies = {
        'openai': 'openai',
        'pandas': 'pandas', 
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'plotly': 'plotly',
        'requests': 'requests',
        'python-dotenv': 'dotenv',
        'openpyxl': 'openpyxl',
        'XlsxWriter': 'xlsxwriter',
        'PyInstaller': 'PyInstaller',
        'urllib3': 'urllib3',
        'certifi': 'certifi',
        'charset-normalizer': 'charset_normalizer',
        'idna': 'idna',
        'tiktoken': 'tiktoken'
    }
    
    missing_deps = []
    installed_versions = {}
    
    for package, import_name in dependencies.items():
        try:
            # Try to import and get version
            result = subprocess.run([
                sys.executable, "-c", 
                f"import {import_name}; print(getattr({import_name}, '__version__', 'unknown'))"
            ], capture_output=True, text=True, check=True)
            
            version = result.stdout.strip()
            print(f"✅ {package} ({version})")
            installed_versions[package] = version
            
        except subprocess.CalledProcessError:
            print(f"❌ {package} - NOT INSTALLED")
            missing_deps.append(package)
    
    if missing_deps:
        print(f"\n⚠️  Missing {len(missing_deps)} dependencies: {', '.join(missing_deps)}")
        print("\n💡 To install missing dependencies:")
        print("   python3 -m pip install -r requirements.txt")
        print("   OR")
        print(f"   python3 -m pip install {' '.join(missing_deps)}")
        return False
    
    return True

def analyze_build_output():
    """Analyze existing build output if present."""
    print("\n🔍 Analyzing build output...")
    
    # Check for existing builds
    dist_path = Path("dist")
    build_path = Path("build")
    
    if not dist_path.exists():
        print("📂 No dist/ directory found - no previous builds")
        return True
    
    # macOS app bundle
    if sys.platform == 'darwin':
        app_path = dist_path / "AI Support Analyzer.app"
        if app_path.exists():
            size_mb = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()) / (1024*1024)
            print(f"📱 Found macOS app: {size_mb:.1f} MB")
            
            if size_mb < 25:
                print("❌ CRITICAL: App too small - missing dependencies!")
                print("   Expected size: 35-50 MB")
                print("   Actual size suggests major dependencies missing")
                return False
            elif size_mb < 35:
                print("⚠️  WARNING: App smaller than expected")
                print("   Some dependencies might be missing")
            else:
                print("✅ App size looks good")
    
    # Windows/Linux executable  
    else:
        exe_path = dist_path / "AI_Support_Analyzer"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024*1024)
            print(f"💻 Found executable: {size_mb:.1f} MB")
            
            if size_mb < 25:
                print("❌ CRITICAL: Executable too small - missing dependencies!")
                print("   Expected size: 35-50 MB")
                return False
            elif size_mb < 35:
                print("⚠️  WARNING: Executable smaller than expected")
            else:
                print("✅ Executable size looks good")
    
    # Check build directory for clues
    if build_path.exists():
        print("📂 Build directory exists - previous builds detected")
        
        # Look for common warning files
        warn_file = build_path / "warn-gui_app.txt"
        if warn_file.exists():
            print("📋 Found PyInstaller warnings - checking...")
            try:
                with open(warn_file, 'r') as f:
                    content = f.read()
                    if 'hidden import' in content.lower():
                        print("⚠️  Hidden import warnings found - dependencies may be missing")
            except:
                pass
    
    return True

def test_gui_import():
    """Test if GUI can be imported without errors."""
    print("\n🖥️  Testing GUI import...")
    
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import gui_app; print('GUI import successful')"
        ], capture_output=True, text=True, check=True, timeout=10)
        
        print("✅ GUI imports successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ GUI import failed!")
        print(f"   Error: {e.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  GUI import timed out - might have dependency issues")
        return False

def provide_recommendations():
    """Provide troubleshooting recommendations."""
    print("\n💡 Build Troubleshooting Recommendations:")
    print()
    print("1. CLEAN BUILD:")
    print("   rm -rf build/ dist/")
    print("   python3 build_executable.py")
    print()
    print("2. FORCE REINSTALL DEPENDENCIES:")
    print("   python3 -m pip uninstall -y -r requirements.txt")
    print("   python3 -m pip install -r requirements.txt")
    print()
    print("3. VIRTUAL ENVIRONMENT (Recommended):")
    print("   python3 -m venv ai_analyzer_env")
    print("   source ai_analyzer_env/bin/activate")
    print("   python3 -m pip install -r requirements.txt")
    print("   python3 build_executable.py")
    print()
    print("4. CHECK SYSTEM ARCH:")
    print("   uname -m  # Should match target system")
    print()
    print("5. PYINSTALLER DEBUG:")
    print("   pyinstaller --debug=all wordpress_support_analyzer.spec")

def main():
    """Main verification routine."""
    print("🔧 AI Support Analyzer - Build Verification")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 5
    
    # Run all checks
    if check_python_version():
        checks_passed += 1
    
    if check_required_files():
        checks_passed += 1
    
    if check_dependencies():
        checks_passed += 1
    
    if analyze_build_output():
        checks_passed += 1
        
    if test_gui_import():
        checks_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Verification Summary: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("✅ All checks passed! Build should work correctly.")
        print("   Ready to build with: python3 build_executable.py")
    elif checks_passed >= 3:
        print("⚠️  Most checks passed, but some issues detected.")
        print("   Build might work but may have problems.")
    else:
        print("❌ Multiple issues detected!")
        print("   Fix issues before attempting to build.")
        
    # Always show recommendations
    provide_recommendations()

if __name__ == "__main__":
    main() 