"""The skill folder and ZIP match the official format; no personal data; stdlib-only scripts."""
import ast
import os
import re
import shutil
import subprocess
import sys
import unittest
import zipfile

from helpers import ROOT, SCRIPTS, SKILL

sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_skill_zip  # noqa: E402
import privacy_scan  # noqa: E402

STDLIB_ONLY = ["kairo_lib.py", "truth_check.py", "jd_scan.py", "form_answers.py", "build_cv_pdf.py"]
LOCAL = {"kairo_lib", "truth_check", "jd_scan", "form_answers"}


class Package(unittest.TestCase):
    def test_zip_builds_and_has_folder_at_top(self):
        self.assertEqual(build_skill_zip.build(), 0)
        with zipfile.ZipFile(build_skill_zip.OUT) as z:
            names = z.namelist()
            skill_md = z.read("kairo/SKILL.md").decode()
        self.assertEqual({n.split("/")[0] for n in names}, {"kairo"})
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith((".pyc", ".DS_Store"))])
        fm = build_skill_zip.frontmatter(skill_md)
        self.assertEqual(fm["name"], "kairo")
        self.assertLessEqual(len(fm["description"]), 200)
        self.assertLess(os.path.getsize(build_skill_zip.OUT), 2 * 1024 * 1024)

    def test_validator_rejects_bad_skills(self):
        tmp = os.path.join(ROOT, "tests", "output", "badskill", "kairo-x")
        shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
        os.makedirs(tmp)
        with open(os.path.join(tmp, "SKILL.md"), "w") as fh:
            fh.write("---\nname: Kairo\ndescription: " + "x" * 250 + "\n---\nSee `scripts/missing.py`.\n")
        probs = " | ".join(build_skill_zip.validate(tmp))
        for bit in ("must match folder", "lowercase", "chars", "missing file"):
            self.assertIn(bit, probs)

    def test_no_personal_data(self):
        self.assertEqual(privacy_scan.scan(), {})

    def test_scripts_import_only_stdlib_at_top(self):
        allowed = set(getattr(sys, "stdlib_module_names", ())) | LOCAL | {"__future__"}
        for name in STDLIB_ONLY:
            with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in tree.body:
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [(node.module or "").split(".")[0]]
                for m in mods:
                    if allowed:
                        self.assertIn(m, allowed, f"{name} imports {m} at top level")

    def test_scripts_compile_on_system_python(self):
        py = shutil.which("python3", path="/usr/bin:/bin")
        if not py:
            self.skipTest("no system python3")
        for name in STDLIB_ONLY:
            p = subprocess.run([py, "-c", f"import ast,sys; ast.parse(open(sys.argv[1]).read())", os.path.join(SCRIPTS, name)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_every_reference_in_skill_md_exists(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        refs = set(re.findall(r"`((?:references|templates|scripts|assets)/[A-Za-z0-9_./-]+)`", text))
        self.assertTrue(refs)
        for r in refs:
            self.assertTrue(os.path.exists(os.path.join(SKILL, r)), r)

    def test_dashboard_link_lives_only_in_config_and_is_on(self):
        import json
        with open(os.path.join(SKILL, "config.json"), encoding="utf-8") as fh:
            cfg = json.load(fh)
        self.assertIs(cfg["launched"], True)
        url = cfg["dashboard_url"].split("://", 1)[1]
        model_names = ("Sonnet", "Opus", "Haiku")
        for base, _, names in os.walk(SKILL):
            for n in names:
                if n.endswith((".md", ".py", ".json", ".txt")):
                    p = os.path.join(base, n)
                    with open(p, encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                    if n != "config.json":
                        self.assertNotIn(url, text, p)
                    if n != "model-tips.md":
                        for m in model_names:
                            self.assertNotIn(m, text, p)

    def test_skill_md_rules_present(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        for must in ("**Maybe**", "**Skip** only when", "Never guess money", "One next step", "make **only the CV**",
                     "Your dashboard is updated.", "config.json", "references/model-tips.md", "apply anyway"):
            self.assertIn(must, text)

    def test_font_licence_is_bundled(self):
        self.assertTrue(os.path.exists(os.path.join(SKILL, "assets", "fonts", "OFL.txt")))


if __name__ == "__main__":
    unittest.main()
