"""Check local publication metadata before creating a GitHub release."""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def publication_errors(root: Path = ROOT) -> list[str]:
    """Return actionable errors without relying on a GitHub account or network."""
    manifest = json.loads((root / "custom_components/ontech/manifest.json").read_text())
    errors = []
    owners = manifest.get("codeowners", [])
    if not owners or any(not re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9-]*", owner) for owner in owners):
        errors.append("Set codeowners to the maintainer's actual GitHub username (with @).")
    documentation = manifest.get("documentation", "")
    match = re.fullmatch(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", documentation)
    if not match:
        errors.append("Set documentation to this integration's public GitHub repository URL.")
    elif manifest.get("issue_tracker") != f"{documentation}/issues":
        errors.append("Set issue_tracker to the repository's /issues URL.")
    if not manifest.get("issue_tracker"):
        errors.append("Add an issue_tracker URL for integration bug reports.")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if repository and match and match[1].lower() != repository.lower():
        errors.append("The documentation URL does not match GITHUB_REPOSITORY.")
    ref = os.environ.get("GITHUB_REF", "")
    if (
        ref.startswith("refs/tags/")
        and ref.removeprefix("refs/tags/").removeprefix("v") != manifest["version"]
    ):
        errors.append("The release tag must match manifest.json version.")
    for filename in (
        "hacs.json",
        "LICENSE",
        "README.md",
        "custom_components/ontech/brand/icon.png",
    ):
        if not (root / filename).is_file():
            errors.append(f"Missing required publication file: {filename}")
    return errors


if __name__ == "__main__":
    errors = publication_errors()
    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print("Local publication metadata is complete. Run HACS validation before publishing.")
    raise SystemExit(bool(errors))
