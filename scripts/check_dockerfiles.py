#!/usr/bin/env python3
"""Validate the shell inside every RUN before paying for an image build.

A CM4 build once failed after five and a half minutes on the arm64 runner
because an edit deleted the last command of a `&&`-chain and left the previous
line ending in `&& \`. The continuation swallowed the following comment block
and the RUN became a syntax error. That is a shell bug, and shell bugs can be
found in milliseconds without a builder, a base image, or an architecture.

Checks per Dockerfile:
  1. No line-continuation runs straight into a comment (the exact bug above).
  2. Every RUN body parses under `bash -n`.
  3. No RUN body ends dangling on `&&`, `||` or `|`.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _logical_lines(text: str):
    """Yield (start_line_no, joined_text, raw_lines) for each instruction."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("#") or not lines[i].strip():
            i += 1
            continue
        start = i
        raw = [lines[i]]
        while lines[i].rstrip().endswith("\\") and i + 1 < len(lines):
            i += 1
            raw.append(lines[i])
        yield start + 1, "\n".join(raw), raw
        i += 1


def check(path: Path) -> list:
    problems = []
    text = path.read_text()
    lines = text.splitlines()

    # 1. continuation into a comment
    for idx, line in enumerate(lines[:-1]):
        if line.rstrip().endswith("\\") and lines[idx + 1].lstrip().startswith("#"):
            problems.append(
                f"{path}:{idx + 1}: line continuation runs into a comment — the RUN "
                f"will swallow the comment block and break\n      {line.strip()[:80]}")

    # 2 + 3. shell validity of each RUN
    for lineno, joined, raw in _logical_lines(text):
        if not joined.lstrip().upper().startswith("RUN "):
            continue
        body = re.sub(r"^\s*RUN\s+", "", joined, count=1)
        if body.lstrip().startswith("["):      # exec form, not shell
            continue
        body = body.replace("\\\n", "\n")
        stripped = body.rstrip()
        if stripped.endswith(("&&", "||", "|")):
            problems.append(
                f"{path}:{lineno}: RUN ends dangling on "
                f"'{stripped[-2:].strip()}' — a command was removed from the chain")
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
            fh.write(body + "\n")
            tmp = fh.name
        r = subprocess.run(["bash", "-n", tmp], capture_output=True, text=True)
        Path(tmp).unlink(missing_ok=True)
        if r.returncode != 0:
            err = (r.stderr or "").strip().splitlines()
            detail = err[-1] if err else "syntax error"
            problems.append(f"{path}:{lineno}: RUN body is not valid shell — {detail}")
    return problems


def main() -> int:
    targets = sorted(ROOT.glob("*/Dockerfile"))
    if not targets:
        print("no Dockerfiles found", file=sys.stderr)
        return 2
    all_problems = []
    for t in targets:
        p = check(t)
        print(f"  {'FAIL' if p else 'ok  '}  {t.relative_to(ROOT)}")
        all_problems += p
    if all_problems:
        print(f"\nDockerfile check FAILED ({len(all_problems)} issue(s)):\n")
        for p in all_problems:
            print(f"  - {p}")
        return 1
    print("\nAll Dockerfiles parse as valid shell.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
