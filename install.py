#!/usr/bin/env python
"""
Install Dependencies Script
One-click installation of all required packages
"""

import sys
import subprocess
from pathlib import Path


def main():
    print("=" * 70)
    print("Network Usage Analysis Tool - Dependency Installation")
    print("=" * 70)
    print()
    
    requirements_file = Path(__file__).with_name('requirements.txt')
    if not requirements_file.exists():
        print(f"❌ requirements.txt not found at: {requirements_file}")
        return 1

    print("Installing required packages from requirements.txt...")
    print()

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file)
        ])

        print("=" * 70)
        print("✅ All dependencies installed successfully!")
        print("=" * 70)
        print()
        print("Next step: Run the application with:")
        print("  python app.py")
        print()
        print("Optional desktop mode:")
        print("  python desktop_app.py")
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
        print(f"  {sys.executable} -m pip install --upgrade pip")
        print(f"  {sys.executable} -m pip install -r requirements.txt")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
