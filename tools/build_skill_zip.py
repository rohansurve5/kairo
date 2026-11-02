#!/usr/bin/env python3
"""Build and validate dist/kairo-skill.zip, the file users upload in Claude.ai (Customize > Skills).

Checks (from Anthropic's skill docs and the Agent Skills spec, see docs/DECISIONS.md):
  * the ZIP's top level is one folder named like the skill ("kairo/"), with kairo/SKILL.md inside
  * SKILL.md starts with YAML frontmatter; name = folder name, lowercase/digits/hyphens, <= 64 chars,
    no leading/trailing/double hyphens, no reserved words; description non-empty, <= 200 chars
    (the stricter of the two published limits), no XML tags
  * SKILL.md under 500 lines; every file it mentions exists
  * no junk files, total size far below 30 MB, no personal data (privacy_scan)
Usage: python3 tools/build_skill_zip.py
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "skill", "kairo")
OUT = os.path.join(ROOT, "dist", "kairo-skill.zip")
JUNK = re.compile(r"(__pycache__|\.pyc$|\.DS_Store$|\.swp$|~$|^\._)")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
        if mm:
            out[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    return out


def validate(skill_dir):
    problems = []
    folder = os.path.basename(skill_dir)
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(path):
        return [f"missing {folder}/SKILL.md"]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fm = frontmatter(text)
    if fm is None:
        return ["SKILL.md does not start with YAML frontmatter (--- ... ---)"]
    name, desc = fm.get("name", ""), fm.get("description", "")
    if name != folder:
        problems.append(f"name '{name}' must match folder '{folder}'")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        problems.append("name: lowercase letters, digits and single hyphens only, max 64")
    if re.search(r"anthropic|claude", name):
        problems.append("name must not contain reserved words")
    if not desc:
        problems.append("description is empty")
    if len(desc) > 200:
        problems.append(f"description is {len(desc)} chars (keep <= 200)")
    if re.search(r"<[^>]+>", name + desc):
        problems.append("no XML tags in name/description")
    extra = set(fm) - {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    if extra:
        problems.append(f"frontmatter fields not in the spec: {sorted(extra)}")
    lines = text.count("\n") + 1
    if lines >= 500:
        problems.append(f"SKILL.md has {lines} lines (keep under 500)")
    for ref in sorted(set(re.findall(r"`((?:references|templates|scripts|assets)/[A-Za-z0-9_./-]+)`", text))):
        if not os.path.exists(os.path.join(skill_dir, ref)):
            problems.append(f"SKILL.md mentions missing file {ref}")
    return problems


def build():
    problems = validate(SKILL_DIR)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from privacy_scan import scan
    leaks = scan(["skill"])
    if leaks:
        problems.append(f"privacy scan found personal terms in: {sorted(leaks)}")
    if problems:
        print("Kairo skill ZIP: NOT built")
        for p in problems:
            print("  -", p)
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    entries = []
    for base, dirs, names in os.walk(SKILL_DIR):
        dirs[:] = sorted(d for d in dirs if not JUNK.search(d))
        for n in sorted(names):
            if JUNK.search(n):
                continue
            full = os.path.join(base, n)
            entries.append((full, os.path.join("kairo", os.path.relpath(full, SKILL_DIR))))
    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for full, arc in entries:
            info = zipfile.ZipInfo(arc, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if arc.endswith(".py") else 0o644) << 16
            with open(full, "rb") as fh:
                data = fh.read()
            total += len(data)
            z.writestr(info, data)
    with zipfile.ZipFile(OUT) as z:
        names = z.namelist()
    tops = {n.split("/")[0] for n in names}
    assert tops == {"kairo"}, tops
    assert "kairo/SKILL.md" in names
    if total > 30 * 1024 * 1024:
        print(f"Kairo skill ZIP: too big ({total} bytes uncompressed)")
        return 1
    print(f"Kairo skill ZIP: OK  {os.path.relpath(OUT, ROOT)}  files={len(names)}  "
          f"uncompressed={total / 1024:.0f} KB  zip={os.path.getsize(OUT) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(build())
