#!/usr/bin/env python
"""
Quick Start Guide for Network Usage Analysis Tool
Run this script to verify installation and dependencies
"""

import sys
import subprocess


def check_python_version():
    """Check if Python 3.7+ is installed"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python 3.7+ required (found {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['psutil', 'matplotlib']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            missing.append(package)
    
    if missing:
        print("\n❌ Missing dependencies. Installing...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing
        )
        print("✅ Dependencies installed successfully!")
        return True
    
    print("\n✅ All dependencies are satisfied!")
    return True


def check_admin_privileges():
    """Check admin privileges (Windows)"""
    try:
        import ctypes
        is_admin = ctypes.windll.shell.IsUserAnAdmin()
        if is_admin:
            print("✅ Running with Administrator privileges")
            return True
        else:
            print("⚠️  Not running as Administrator (optional but recommended)")
            return True
    except:
        print("⚠️  Could not verify Administrator privileges (non-Windows?)")
        return True


def main():
    """Run all checks"""
    print("=" * 60)
    print("Network Usage Analysis Tool - System Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Administrator Privileges", check_admin_privileges),
    ]
    
    results = []
    for name, check in checks:
        print(f"\n[{name}]")
        try:
            result = check()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error during check: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    if all(r for _, r in results):
        print("\n" + "=" * 60)
        print("✅ All checks passed! Ready to run.")
        print("=" * 60)
        print("\nTo start the application, run:")
        print("  python main.py")
        print("\nOr with administrator privileges:")
        print("  Right-click main.py → Run as Administrator")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ Some checks failed. Please resolve the issues above.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
