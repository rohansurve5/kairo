#!/usr/bin/env python3
"""Scan Kairo files for personal data from the old single-user system.

The forbidden words (the original owner's name, contacts, employers, agencies, coach material) are
stored only as SHA-256 hashes, so this repository never contains them in plain text.
Every 1-, 2- and 3-word sequence in each scanned file is hashed and compared.

Usage: python3 tools/privacy_scan.py [paths...]   (default: skill docs tests/fixtures CLAUDE.md README.md)
Exit 0 = clean, 1 = found something.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENY = {
    "175fe25e87635a04", "4c1be7f5982f74ae", "1f60dde634ad3452", "b22796124e7d4241", "8cb3a73d22260d58",
    "23553f21d0df6b1a", "964f27e353d7cf68", "17ad1f0e7556ae4d", "0b9ee0b94db97ea7", "e6cfb55d29bade27",
    "8e62be434ac06469", "e894462a4e2e3e3e", "4a81428868842730", "4e64f4e6eaa5b906", "b72db39b6e5ec0f8",
    "784dabc8374d3458", "8d71cf721799dee0", "7f17dfab0c3ea669", "699d1f2e31611fe6", "779fcd33d45f1772",
}
# The maintainer's public name and GitHub handle (hashes): allowed ONLY in the public owner files below
# (README credit, security contact, changelog links). Every other forbidden term is still blocked there.
PUBLIC_IDENTITY = {"175fe25e87635a04", "4c1be7f5982f74ae", "b72db39b6e5ec0f8", "1f60dde634ad3452"}
OWNER_FILES = {"README.md", "SECURITY.md", "CHANGELOG.md", "CONTRIBUTING.md"}
TEXT_EXT = {"", ".md", ".py", ".json", ".txt", ".html", ".toml", ".yml", ".yaml", ".csv"}
LICENCE_FILES = {"LICENSE", "LICENSE.txt"}
DEFAULT = ["skill", "docs", "tests/fixtures", "tests/flow", "CLAUDE.md", "README.md", "CONTRIBUTING.md",
           "SECURITY.md", "CHANGELOG.md", "tools"]


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def scan_text(text, allow=frozenset()):
    words = re.findall(r"[a-z0-9]+", text.lower())
    hits = set()
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            k = h(" ".join(words[i:i + n]))
            if k in DENY and k not in allow:
                hits.add((i, n))
    return [" ".join(words[i:i + n]) for i, n in sorted(hits)]


def files(paths):
    for p in paths:
        full = os.path.join(ROOT, p)
        if os.path.isfile(full):
            yield full
        for base, dirs, names in os.walk(full):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".venv")]
            for n in names:
                if os.path.splitext(n)[1].lower() in TEXT_EXT:
                    yield os.path.join(base, n)


def scan(paths=None):
    found = {}
    for f in files(paths or DEFAULT):
        if os.path.abspath(f) == os.path.abspath(__file__):
            continue
        if os.path.basename(f) in LICENCE_FILES:  # the copyright holder's name belongs there
            continue
        with open(f, encoding="utf-8", errors="ignore") as fh:
            owner = os.path.dirname(os.path.abspath(f)) == ROOT and os.path.basename(f) in OWNER_FILES
            hits = scan_text(fh.read(), PUBLIC_IDENTITY if owner else frozenset())
        if hits:
            found[os.path.relpath(f, ROOT)] = len(hits)
    return found


if __name__ == "__main__":
    res = scan(sys.argv[1:] or None)
    if res:
        print("Privacy scan: FOUND forbidden personal terms (shown as counts only):")
        for f, n in res.items():
            print(f"  {f}: {n}")
        sys.exit(1)
    print("Privacy scan: clean")
