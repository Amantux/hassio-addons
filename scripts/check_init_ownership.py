#!/usr/bin/env python3
"""Guard the first-boot ownership race in the add-on init sequence.

cont-init.d runs as root; the Claude tooling in 82-claude_tools.sh runs as the
`abc` runtime user. On a fresh install `$HOME/.claude` does not exist, so a bare
`mkdir -p` there created it root-owned and every subsequent tool write failed:

    tokensave: failed to write .../.claude/settings.json.new: Permission denied
    rtk:       Failed to create temp file in .../.claude: Permission denied

20-folders.sh chowns $HOME recursively but runs earlier, so it cannot cover a
directory created later. 84-claude_runtime_ownership.sh does fix it, but only
after those writes have failed — which is why the integration silently repaired
itself on the SECOND boot and looked like a fluke.

This asserts the directory is created with the runtime identity, and that the
late sweep still exists as a safety net.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(addon: Path) -> list:
    problems = []
    tools = addon / "rootfs/etc/cont-init.d/82-claude_tools.sh"
    sweep = addon / "rootfs/etc/cont-init.d/84-claude_runtime_ownership.sh"

    if not tools.exists():
        return [f"{addon.name}: 82-claude_tools.sh is missing"]
    src = tools.read_text()

    # The tools run as abc, so the identity must be resolved, not assumed.
    if "id -u abc" not in src:
        problems.append(
            f"{addon.name}: 82 must derive the runtime uid with `id -u abc` "
            "(PUID is user-configurable — 65000 on real installs, not 1000)")

    # Every `mkdir -p "$HOME/.claude"` must be followed closely by a chown.
    for m in re.finditer(r'mkdir -p "\$HOME/\.claude"', src):
        window = src[m.end(): m.end() + 260]
        if "chown" not in window:
            line = src[: m.start()].count("\n") + 1
            problems.append(
                f"{addon.name}:82-claude_tools.sh:{line}: creates $HOME/.claude as root "
                "without chowning it to the runtime user — first boot will fail to write "
                "settings.json and RTK.md")

    if "run_as_runtime_user" not in src:
        problems.append(f"{addon.name}: 82 lost its run_as_runtime_user helper")

    # The late sweep must remain: 83 still writes settings.json as root by design.
    if not sweep.exists():
        problems.append(f"{addon.name}: 84-claude_runtime_ownership.sh is missing "
                        "(still needed for paths written as root by 83)")
    elif "chown" not in sweep.read_text():
        problems.append(f"{addon.name}: 84 no longer chowns anything")

    return problems


def main() -> int:
    addons = sorted(p.parent.parent.parent.parent
                    for p in ROOT.glob("*/rootfs/etc/cont-init.d/82-claude_tools.sh"))
    if not addons:
        print("no add-ons with 82-claude_tools.sh found", file=sys.stderr)
        return 2
    problems = []
    for a in addons:
        p = check(a)
        print(f"  {'FAIL' if p else 'ok  '}  {a.name}")
        problems += p
    if problems:
        print(f"\nInit-ownership check FAILED ({len(problems)}):\n")
        for x in problems:
            print(f"  - {x}")
        return 1
    print("\n$HOME/.claude is created with the runtime identity in every add-on.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
