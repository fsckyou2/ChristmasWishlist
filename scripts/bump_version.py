#!/usr/bin/env python3
"""
Semantic Versioning Bump Script

Usage:
    python scripts/bump_version.py [major|minor|patch]

This script:
1. Reads the current version from VERSION file
2. Bumps the specified part (major, minor, or patch)
3. Updates the VERSION file
4. Displays git commands to create and push the tag
"""

import sys
import re
from pathlib import Path


def parse_version(version_str):
    """Parse semantic version string into (major, minor, patch) tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str.strip())
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))


def bump_version(version_tuple, bump_type):
    """Bump the specified part of the version."""
    major, minor, patch = version_tuple

    if bump_type == "major":
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', or 'patch'.")


def format_version(version_tuple):
    """Format version tuple as string."""
    return f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ["major", "minor", "patch"]:
        print("Usage: python scripts/bump_version.py [major|minor|patch]")
        print()
        print("Examples:")
        print("  python scripts/bump_version.py patch   # 1.0.0 -> 1.0.1")
        print("  python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0")
        print("  python scripts/bump_version.py major   # 1.0.0 -> 2.0.0")
        sys.exit(1)

    bump_type = sys.argv[1]

    # Find VERSION file
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    version_file = repo_root / "VERSION"

    if not version_file.exists():
        print(f"ERROR: VERSION file not found at {version_file}")
        sys.exit(1)

    # Read current version
    current_version_str = version_file.read_text().strip()
    try:
        current_version = parse_version(current_version_str)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Bump version
    new_version = bump_version(current_version, bump_type)
    new_version_str = format_version(new_version)

    # Update VERSION file
    version_file.write_text(f"{new_version_str}\n")

    print(f"✓ Version bumped: {current_version_str} -> {new_version_str}")
    print()
    print("Next steps:")
    print("1. Review the version change")
    print("2. Commit the VERSION file:")
    print("   git add VERSION")
    print(f'   git commit -m "Bump version to {new_version_str}"')
    print()
    print("3. Create and push the tag:")
    print(f'   git tag -a v{new_version_str} -m "Release version {new_version_str}"')
    print(f"   git push origin v{new_version_str}")
    print()
    print("4. Push the commit:")
    print("   git push")
    print()
    print(f"This will trigger Docker Hub deployment with tag v{new_version_str}")


if __name__ == "__main__":
    main()
