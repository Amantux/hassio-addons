#!/usr/bin/env python3
"""Keep claude_desktop_cm4 honest against its parent, claude_desktop_dev.

The CM4 add-on is a fork of the dev add-on, not a build variant of it, because
Home Assistant add-on config has no per-architecture `devices:` syntax. A fork
solves that, and buys the usual fork problem: a fix landed in the parent is
silently absent from the child, and nothing complains.

This script makes that visible. Every difference between the two add-ons must be
declared here with a reason. Anything else is drift, and drift fails the build.

    python3 scripts/check_addon_parity.py          # report + exit 1 on drift
    python3 scripts/check_addon_parity.py --list   # show the declared diffs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT / "claude_desktop_dev"
CHILD = ROOT / "claude_desktop_cm4"

# Files that are SUPPOSED to differ, each with the reason it diverges. A file
# listed here is exempt from byte comparison; everything else must match.
INTENTIONAL_DIFFS = {
    "config.yaml": "different slug/name/image, and the CM4 device list omits nodes a Pi lacks",
    "build.json": "aarch64-only base image",
    "Dockerfile": "no x86 virtualization stack, no virtiofsd builder stage",
    "README.md": "board-specific requirements and limitations",
    "CHANGELOG.md": "independent version history",
    "apparmor.txt": "profile renamed so the Supervisor cannot confuse the two",
    "updater.json": "slug points at this add-on so the bot cannot rewrite its sibling",
}

# Config keys that must differ, or the two add-ons collide in Home Assistant.
MUST_DIFFER = ["slug", "name", "image"]

# Config keys that must stay identical: these define shared behaviour, and a
# silent divergence here is exactly the bug this script exists to catch.
MUST_MATCH = ["ingress", "init", "hassio_api", "hassio_role", "homeassistant_api",
              "auth_api", "map", "privileged", "panel_admin", "tmpfs", "udev"]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel_files(base: Path) -> dict:
    return {str(p.relative_to(base)): p for p in base.rglob("*") if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print the declared differences")
    args = ap.parse_args()

    if args.list:
        print("Declared differences between claude_desktop_dev and claude_desktop_cm4:\n")
        for name, why in sorted(INTENTIONAL_DIFFS.items()):
            print(f"  {name:16} {why}")
        return 0

    if not PARENT.is_dir() or not CHILD.is_dir():
        print(f"ERROR: expected both {PARENT.name}/ and {CHILD.name}/", file=sys.stderr)
        return 2

    problems: list[str] = []
    parent_files, child_files = _rel_files(PARENT), _rel_files(CHILD)

    # 1. A file added to the parent and never carried across is the classic
    #    fork-drift failure: the fix exists, just not for Yellow users.
    for missing in sorted(set(parent_files) - set(child_files)):
        problems.append(f"MISSING in cm4: {missing} (added to dev, never forked across)")

    for extra in sorted(set(child_files) - set(parent_files)):
        if extra not in INTENTIONAL_DIFFS:
            problems.append(f"EXTRA in cm4: {extra} (not present in dev, not declared)")

    # 2. Shared files must be byte-identical unless the difference is declared.
    for name in sorted(set(parent_files) & set(child_files)):
        if name in INTENTIONAL_DIFFS:
            continue
        if _digest(parent_files[name]) != _digest(child_files[name]):
            problems.append(
                f"DRIFT: {name} differs but is not declared in INTENTIONAL_DIFFS. "
                "Either port the change, or declare the difference with a reason.")

    # 3. Config keys: some must differ, some must not.
    try:
        import yaml
        pc = yaml.safe_load((PARENT / "config.yaml").read_text())
        cc = yaml.safe_load((CHILD / "config.yaml").read_text())
    except Exception as exc:  # pragma: no cover
        problems.append(f"could not parse config.yaml pair: {exc}")
        pc = cc = None

    if pc and cc:
        for key in MUST_DIFFER:
            if pc.get(key) == cc.get(key):
                problems.append(
                    f"COLLISION: config '{key}' is identical ({pc.get(key)!r}); "
                    "the two add-ons would clash in Home Assistant")
        for key in MUST_MATCH:
            if pc.get(key) != cc.get(key):
                problems.append(
                    f"BEHAVIOUR DRIFT: config '{key}' differs "
                    f"(dev={pc.get(key)!r} cm4={cc.get(key)!r}); "
                    "port it or add the key to the declared exceptions")

        # The whole point of the fork. If these ever come back, the add-on
        # stops starting on a Pi and the reason is invisible from the logs.
        impossible = {"/dev/kvm", "/dev/vhost-vsock", "/dev/dri/card1"}
        present = impossible & set(cc.get("devices") or [])
        if present:
            problems.append(
                f"FATAL: cm4 requires device(s) a Raspberry Pi does not provide: "
                f"{sorted(present)}. Docker refuses to create the container and "
                "the add-on fails to start.")

        if cc.get("image", "") != cc.get("image", "").lower():
            problems.append("cm4 image ref is not lowercase; GHCR rejects mixed-case namespaces")

        if cc.get("arch") != ["aarch64"]:
            problems.append(f"cm4 arch should be ['aarch64'], got {cc.get('arch')!r}")

    if problems:
        print(f"Add-on parity check FAILED ({len(problems)} issue(s)):\n")
        for p in problems:
            print(f"  - {p}")
        print("\nDeclare intended differences in INTENTIONAL_DIFFS, or port the change.")
        return 1

    shared = len(set(parent_files) & set(child_files)) - len(INTENTIONAL_DIFFS)
    print(f"Add-on parity OK: {shared} shared files identical, "
          f"{len(INTENTIONAL_DIFFS)} declared differences.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
