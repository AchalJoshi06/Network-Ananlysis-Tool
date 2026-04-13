#!/usr/bin/env python
"""
Install Dependencies Script
One-click installation of all required packages
"""

import sys
import subprocess


def main():
    print("=" * 70)
    print("Network Usage Analysis Tool - Dependency Installation")
    print("=" * 70)
    print()
    
    print("Installing required packages...")
    print()
    
    packages = [
        'psutil>=5.9.0',
        'matplotlib>=3.5.0',
    ]
    
    try:
        for package in packages:
            print(f"Installing: {package}")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package]
            )
            print()
        
        print("=" * 70)
        print("✅ All dependencies installed successfully!")
        print("=" * 70)
        print()
        print("Next step: Run the application with:")
        print("  python main.py")
        print()
        return 0
        
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print("❌ Installation failed!")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        print("Try running:")
        print("  pip install --upgrade pip")
        print("  pip install -r requirements.txt")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
