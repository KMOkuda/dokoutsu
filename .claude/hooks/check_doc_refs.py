#!/usr/bin/env python3
"""Warn when an edited Markdown file references a docs/ or .claude/ file that doesn't exist."""
import os
import re
import sys


def find_root(start):
    root = os.path.dirname(os.path.abspath(start))
    while root and not os.path.exists(os.path.join(root, "CLAUDE.md")):
        parent = os.path.dirname(root)
        if parent == root:
            return None
        root = parent
    return root


def main():
    if len(sys.argv) < 2:
        return
    path = sys.argv[1]
    if not path.endswith(".md"):
        return
    root = find_root(path)
    if not root:
        return
    try:
        content = open(path, encoding="utf-8").read()
    except OSError:
        return

    refs = re.findall(r"`((?:docs|\.claude)/[^`]+\.(?:md|pdf|html|json))`", content)
    missing = [r for r in refs if not os.path.exists(os.path.join(root, r))]
    if missing:
        rel = os.path.relpath(path, root)
        print(f"[reference-check] {rel} references missing files:", file=sys.stderr)
        for m in sorted(set(missing)):
            print(f"  - {m}", file=sys.stderr)


if __name__ == "__main__":
    main()
