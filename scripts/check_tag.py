#!/usr/bin/env python3
import sys
import subprocess
import toml

def get_version_from_pyproject():
    try:
        with open("pyproject.toml", "r") as f:
            pyproject = toml.load(f)
        # Poetry projects: version is under [tool.poetry]
        return pyproject["tool"]["poetry"]["version"]
    except Exception as e:
        print(f"Error reading version from pyproject.toml: {e}", file=sys.stderr)
        sys.exit(1)

def get_tags_pointing_at_head():
    try:
        tags = subprocess.check_output(
            ["git", "tag", "--points-at", "HEAD"], encoding="utf-8"
        ).split()
        return tags
    except Exception as e:
        print(f"Error getting git tags: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    version = get_version_from_pyproject()
    tags = get_tags_pointing_at_head()
    expected_tags = [version, f"v{version}"]

    if not any(tag in expected_tags for tag in tags):
        print(
            f"FAIL: No tag matching version '{version}' or 'v{version}' found on current commit.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"PASS: Found tag matching version '{version}' on current commit.")

if __name__ == "__main__":
    main()
