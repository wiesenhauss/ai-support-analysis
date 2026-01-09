#!/usr/bin/env python3
"""
Build script for AI Support Analyzer
Packages the GUI application into a standalone executable

Features:
- Automatic PyInstaller installation if not present
- Version management with incremental updates
- Cross-platform support (macOS, Windows, Linux)
- Comprehensive error handling and logging
"""

import subprocess
import sys
import json
import os
from datetime import datetime
from pathlib import Path

def get_version():
    """Get the current version, incrementing if needed."""
    version_file = Path("version.json")
    
    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                version_data = json.load(f)
            
            current_version = version_data.get('version', '1.4.0')
            print(f"Current version: {current_version}")
            
            # Ask if user wants to increment
            response = input("Increment version? (y/N): ").strip().lower()
            if response == 'y':
                parts = current_version.split('.')
                if len(parts) >= 3:
                    # Increment patch version
                    parts[2] = str(int(parts[2]) + 1)
                    new_version = '.'.join(parts)
                else:
                    new_version = current_version + ".1"
                
                version_data['version'] = new_version
                version_data['last_build'] = datetime.now().isoformat()
                
                with open(version_file, 'w') as f:
                    json.dump(version_data, f, indent=2)
                
                print(f"Version updated to: {new_version}")
                return new_version
            else:
                return current_version
                
        except (json.JSONDecodeError, KeyError):
            print("Invalid version file, using default version")
    
    # Default version
    default_version = "1.4.0"
    version_data = {
        'version': default_version,
        'last_build': datetime.now().isoformat()
    }
    
    with open(version_file, 'w') as f:
        json.dump(version_data, f, indent=2)
    
    return default_version

def check_and_install_dependencies():
    """Check and install all required dependencies."""
    print("🔍 Checking project dependencies...")
    
    # Required packages for the application
    required_packages = [
        'openai',
        'pandas', 
        'numpy',
        'matplotlib',
        'seaborn',
        'plotly',
        'requests',
        'python-dotenv',
        'openpyxl',
        'XlsxWriter',
        'PyInstaller'
    ]
    
    missing_packages = []
    
    # Check each package
    for package in required_packages:
        try:
            if package == 'XlsxWriter':
                test_import = 'xlsxwriter'
            elif package == 'python-dotenv':
                test_import = 'dotenv'
            else:
                test_import = package.lower()
                
            subprocess.run([sys.executable, "-c", f"import {test_import}"], 
                          capture_output=True, check=True)
            print(f"✅ {package}")
        except subprocess.CalledProcessError:
            print(f"❌ {package} not found")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Missing {len(missing_packages)} packages: {', '.join(missing_packages)}")
        print("📦 Auto-installing missing dependencies...")
        
        # Try to install from requirements.txt first
        if os.path.exists('requirements.txt'):
            print("📦 Installing all dependencies from requirements.txt...")
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                                      check=True, capture_output=True, text=True)
                print("✅ All dependencies installed from requirements.txt!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Requirements.txt installation failed, trying individual packages...")
                print(f"   Error: {e.stderr.strip() if e.stderr else 'Unknown error'}")
        
        # Fallback to individual package installation
        print(f"📦 Installing {len(missing_packages)} missing packages individually...")
        
        failed_packages = []
        for package in missing_packages:
            try:
                print(f"   Installing {package}...")
                subprocess.run([sys.executable, "-m", "pip", "install", package], 
                              check=True, capture_output=True, text=True)
                print(f"   ✅ {package} installed")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Failed to install {package}: {e.stderr.strip() if e.stderr else 'Unknown error'}")
                failed_packages.append(package)
        
        if failed_packages:
            print(f"\n❌ Failed to install {len(failed_packages)} packages: {', '.join(failed_packages)}")
            print("💡 Try running manually: python3 -m pip install " + " ".join(failed_packages))
            return False
        
        print("✅ All dependencies installed successfully!")
    
    return True

def check_requirements():
    """Check all build requirements."""
    print("🔍 Checking build requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check and install all dependencies
    if not check_and_install_dependencies():
        return False
    
    # Check spec file
    spec_file = "wordpress_support_analyzer.spec"
    if not os.path.exists(spec_file):
        print(f"❌ Error: {spec_file} not found!")
        return False
    print(f"✅ Spec file found: {spec_file}")
    
    # Check main GUI file
    if not os.path.exists('gui_app.py'):
        print("❌ gui_app.py not found")
        return False
    print("✅ GUI application file found")
    
    return True

def build_executable():
    """Build the executable using PyInstaller."""
    print("=" * 60)
    print("🚀 Building AI Support Analyzer")
    print("=" * 60)
    
    # Check all requirements first
    if not check_requirements():
        return False
    
    # Get version
    version = get_version()
    
    # Build command
    spec_file = "wordpress_support_analyzer.spec"
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm", 
        spec_file
    ]
    
    print(f"📦 Building version {version}...")
    print(f"💻 Command: {' '.join(build_cmd)}")
    print()
    
    try:
        # Run the build
        result = subprocess.run(build_cmd, check=True, capture_output=True, text=True)
        
        print("✅ Build completed successfully!")
        print()
        
        # Check output files and validate
        if sys.platform == 'darwin':
            app_path = Path("dist/AI Support Analyzer.app")
            if app_path.exists():
                size_mb = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()) / (1024*1024)
                print(f"📱 macOS App: {app_path}")
                print(f"📏 Size: {size_mb:.1f} MB")
                
                # Validate size - should be at least 30MB for a proper build
                if size_mb < 30:
                    print("⚠️  WARNING: App size is unusually small!")
                    print("   This suggests dependencies may not be properly bundled.")
                    print("   Expected size: 35-50 MB")
                    print("   Try installing missing dependencies and rebuilding.")
                    return False
                elif size_mb > 30:
                    print("✅ App size looks good - dependencies properly bundled")
            else:
                print("❌ Error: App bundle not found")
                return False
        else:
            exe_path = Path("dist/AI_Support_Analyzer")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024*1024)
                print(f"💻 Executable: {exe_path}")
                print(f"📏 Size: {size_mb:.1f} MB")
                
                # Validate size - should be at least 30MB for a proper build
                if size_mb < 30:
                    print("⚠️  WARNING: Executable size is unusually small!")
                    print("   This suggests dependencies may not be properly bundled.")
                    print("   Expected size: 35-50 MB")
                    print("   Try installing missing dependencies and rebuilding.")
                    return False
                elif size_mb > 30:
                    print("✅ Executable size looks good - dependencies properly bundled")
            else:
                print("❌ Error: Executable not found")
                return False
        
        print()
        print("🎉 Build process completed!")
        print(f"📋 Version: {version}")
        print(f"📅 Built: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ Build failed!")
        print("STDERR:", e.stderr)
        print("STDOUT:", e.stdout)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1) 