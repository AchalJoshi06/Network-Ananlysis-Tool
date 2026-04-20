#!/usr/bin/env python
"""Project setup verification for the current Flask/desktop app stack."""

import importlib
import re
import sys
from pathlib import Path


MIN_PYTHON = (3, 10)
REQUIREMENTS_PATH = Path(__file__).with_name('requirements.txt')

# Package names in requirements.txt do not always match import names.
IMPORT_NAME_MAP = {
    'Flask': 'flask',
    'python-whois': 'whois',
    'PyQt6-WebEngine': 'PyQt6.QtWebEngineWidgets',
}


def _extract_package_name(requirement_line: str) -> str:
    """Extract package name from requirement expression."""
    return re.split(r'[<>=!~\[]', requirement_line.strip(), maxsplit=1)[0]


def _load_required_packages() -> list:
    """Load package names from requirements.txt."""
    if not REQUIREMENTS_PATH.exists():
        raise FileNotFoundError(f"requirements.txt not found at {REQUIREMENTS_PATH}")

    packages = []
    for line in REQUIREMENTS_PATH.read_text(encoding='utf-8').splitlines():
        clean = line.strip()
        if not clean or clean.startswith('#'):
            continue
        packages.append(_extract_package_name(clean))
    return packages


def check_python_version() -> bool:
    """Check if the project's minimum Python version is available."""
    version = sys.version_info
    if (version.major, version.minor) < MIN_PYTHON:
        print(
            f"[FAIL] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required "
            f"(found {version.major}.{version.minor}.{version.micro})"
        )
        return False
    print(f"[PASS] Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def check_dependencies() -> bool:
    """Validate all dependencies declared in requirements.txt."""
    try:
        required_packages = _load_required_packages()
    except Exception as exc:
        print(f"[FAIL] Could not read requirements.txt: {exc}")
        return False

    missing = []
    for package in required_packages:
        import_name = IMPORT_NAME_MAP.get(package, package.replace('-', '_'))
        try:
            importlib.import_module(import_name)
            print(f"[PASS] {package} ({import_name})")
        except Exception:
            print(f"[FAIL] {package} ({import_name})")
            missing.append(package)

    if missing:
        print("\nMissing packages detected:")
        for package in missing:
            print(f"- {package}")
        print("\nInstall with:")
        print(f"  {sys.executable} -m pip install -r requirements.txt")
        return False

    print("\n[PASS] All dependencies from requirements.txt are installed")
    return True


def check_admin_privileges() -> bool:
    """Check admin privileges (Windows) for full process visibility."""
    try:
        import ctypes

        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if is_admin:
            print("[PASS] Running with Administrator privileges")
        else:
            print("[WARN] Not running as Administrator (recommended for full visibility)")
        return True
    except Exception:
        print("[WARN] Could not verify Administrator privileges")
        return True


def main() -> int:
    """Run all setup checks and print current run instructions."""
    print("=" * 70)
    print("Network Analysis Tool - Setup Check")
    print("=" * 70)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Administrator Privileges", check_admin_privileges),
    ]

    results = []
    for name, check in checks:
        print(f"\n[{name}]")
        try:
            results.append((name, check()))
        except Exception as exc:
            print(f"[FAIL] Error during check: {exc}")
            results.append((name, False))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    for name, result in results:
        print(f"{'[PASS]' if result else '[FAIL]'} {name}")

    if all(result for _, result in results):
        print("\nEnvironment looks good. Start the app with:")
        print("  python app.py")
        print("Optional desktop mode:")
        print("  python desktop_app.py")
        return 0

    print("\nFix failed checks, then re-run this script.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
