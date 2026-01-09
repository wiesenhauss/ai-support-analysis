#!/usr/bin/env python3
"""
Simple build script for AI Support Analyzer
Quick compilation without version management

Features:
- Automatic PyInstaller installation
- Basic requirement checking
- Fast build process
"""

import subprocess
import sys
import os

def check_and_install_dependencies():
    """Check if required dependencies are installed, install if not."""
    print("🔍 Checking dependencies...")
    
    # Essential packages
    required_packages = ['PyInstaller', 'openai', 'pandas', 'matplotlib', 'tiktoken']
    missing_packages = []
    
    for package in required_packages:
        try:
            test_import = 'pyinstaller' if package == 'PyInstaller' else package.lower()
            subprocess.run([sys.executable, "-c", f"import {test_import}"], 
                          capture_output=True, check=True)
            print(f"✅ {package}")
        except subprocess.CalledProcessError:
            print(f"❌ {package} not found")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 Auto-installing {len(missing_packages)} missing packages...")
        
        # Try requirements.txt first if available
        if os.path.exists('requirements.txt') and len(missing_packages) > 2:
            print("📦 Installing from requirements.txt...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              check=True, capture_output=True, text=True)
                print("✅ Dependencies installed from requirements.txt!")
                return True
            except subprocess.CalledProcessError as e:
                print("⚠️  Requirements.txt failed, installing individually...")
                print(f"   Error: {e.stderr.strip() if e.stderr else 'Unknown error'}")
        
        # Install individual packages
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
    
    return True

def main():
    print("🚀 Building AI Support Analyzer (Quick Build)...")
    
    # Check requirements
    if not check_and_install_dependencies():
        print("❌ Cannot proceed without required dependencies")
        sys.exit(1)
    
    if not os.path.exists("wordpress_support_analyzer.spec"):
        print("❌ Spec file not found!")
        sys.exit(1)
    
    if not os.path.exists("gui_app.py"):
        print("❌ GUI app file not found!")
        sys.exit(1)
    
    cmd = [
        sys.executable, "-m", "PyInstaller", 
        "--clean", 
        "--noconfirm", 
        "wordpress_support_analyzer.spec"
    ]
    
    print(f"💻 Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Build completed!")
        
        # Show output info and validate
        if sys.platform == 'darwin':
            app_path = "dist/AI Support Analyzer.app"
            print(f"📱 macOS App: {app_path}")
            
            # Check size
            if os.path.exists(app_path):
                size_mb = sum(os.path.getsize(os.path.join(dirpath, filename))
                             for dirpath, dirnames, filenames in os.walk(app_path)
                             for filename in filenames) / (1024*1024)
                print(f"📏 Size: {size_mb:.1f} MB")
                
                if size_mb < 30:
                    print("⚠️  WARNING: App size unusually small - dependencies may be missing!")
                    print("   Try: python3 -m pip install -r requirements.txt")
                else:
                    print("✅ Size looks good - ready for distribution")
        else:
            exe_path = "dist/AI_Support_Analyzer"
            print(f"💻 Executable: {exe_path}")
            
            # Check size
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024*1024)
                print(f"📏 Size: {size_mb:.1f} MB")
                
                if size_mb < 30:
                    print("⚠️  WARNING: Executable size unusually small - dependencies may be missing!")
                    print("   Try: python3 -m pip install -r requirements.txt")
                else:
                    print("✅ Size looks good - ready for distribution")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 