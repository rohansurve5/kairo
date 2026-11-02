#!/usr/bin/env python3
"""Run Kairo's script steps end to end for the fake user (Priya Sharma) and the 3 sample JDs.

The AI steps (reading the JD, final score, reasons, writing cv.json / letter.json) are done by
Claude in Claude.ai. Here they are stood in by the fixture files; the written fit-check replies are
in tests/flow/fit-check-replies.md. Output: tests/output/flow/ and tests/output/flow-summary.md.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import date

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from helpers import FACTS, OUTPUT, SCRIPTS, fixture  # noqa: E402

import form_answers  # noqa: E402
import jd_scan  # noqa: E402
import truth_check  # noqa: E402
from kairo_lib import load_facts, read_text  # noqa: E402

TODAY = date(2026, 11, 2)
OUT = os.path.join(OUTPUT, "flow")
JOBS = [
    dict(key="in", jd="jd-in-bengaluru.txt", country="IN", title="Product Manager – Merchant Payments",
         company="Nirvana Ledger", city="Bengaluru", source="linkedin", posted=None),
    dict(key="nl", jd="jd-nl-amsterdam.txt", country="NL", title="Product Manager, Merchant Checkout",
         company="Tulip Commerce B.V.", city="Amsterdam", source="company_site", posted="2026-10-25"),
    dict(key="ae", jd="jd-ae-dubai.txt", country="AE", title="Senior Product Manager – Loyalty & CRM",
         company="Falcon Retail Group", city="Dubai", source="other", posted=None),
]


def build(args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build_cv_pdf.py")] + args, capture_output=True, text=True, env=env)
    res = next((json.loads(ln[len("KAIRO_RESULT "):]) for ln in p.stdout.splitlines() if ln.startswith("KAIRO_RESULT ")), None)
    return p.returncode, res, p.stdout


def header_line(pdf):
    from pypdf import PdfReader
    text = PdfReader(pdf).pages[0].extract_text() or ""
    return text.splitlines()[2] if len(text.splitlines()) > 2 else ""


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, ok = [], True
    rep, facts = truth_check.run(FACTS, lint=True)
    rows.append(("Setup", "my-facts.md lint", "PASS" if not rep.errors else "FAIL", f"{len(facts['jobs'])} jobs, {len(facts['skills'])} skills"))
    ok &= not rep.errors
    facts = load_facts(FACTS)

    for j in JOBS:
        jd = read_text(fixture(j["jd"]))
        r = jd_scan.scan(facts, jd, j["country"], j["title"], j["company"], j["city"], j["posted"], j["source"], TODAY)
        with open(os.path.join(OUT, f"scan-{j['key']}.json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2, ensure_ascii=False)
        blocks = [f["code"] for f in r["red_flags"] if f["severity"] == "block"]
        warns = [f["code"] for f in r["red_flags"] if f["severity"] == "warn"]
        rows.append((j["key"].upper(), "JD scan", "done",
                     f"baseline {r['baseline']['score']}, sponsorship {r['signals']['sponsorship']['value']}, "
                     f"blocks: {', '.join(blocks) or 'none'}; warns: {', '.join(warns) or 'none'}"))

        fa = form_answers.build(facts, j["country"], jd, company=j["company"], role=j["title"], city=j["city"])
        with open(os.path.join(OUT, f"form-answers-{j['key']}.md"), "w", encoding="utf-8") as fh:
            fh.write(form_answers.to_markdown(fa) + "\n")
        rows.append((j["key"].upper(), "Form answers + salary", "done", fa["salary"]["text"] + f" ({fa['salary']['basis']})"))

        extra = {}
        if j["key"] == "nl":
            extra = dict(letter=fixture("letter-nl.json"), answers=fixture("answers-nl.json"), jd_path=fixture(j["jd"]))
        rep, _ = truth_check.run(FACTS, cv=fixture(f"cv-{j['key']}.json"), **extra)
        rows.append((j["key"].upper(), "Truth check (CV" + (" + letter + answers)" if extra else ")"),
                     "PASS" if not rep.errors else "FAIL", f"{len(rep.warnings)} warnings"))
        ok &= not rep.errors

        pdf = os.path.join(OUT, f"Priya_Sharma_CV_{j['company'].split()[0]}.pdf")
        code, res, log = build([fixture(f"cv-{j['key']}.json"), "--facts", FACTS, "--out", pdf])
        good = code == 0 and res and res.get("pages", 9) <= 2 and not res.get("missing_words")
        rows.append((j["key"].upper(), "CV PDF", "PASS" if good else "FAIL",
                     f"{res.get('pages')} page(s), font {res.get('font')}, text extractable, header: {header_line(pdf)}" if res else log[-200:]))
        ok &= bool(good)
        if j["key"] == "nl":
            pdf = os.path.join(OUT, "Priya_Sharma_Cover_Letter_Tulip.pdf")
            code, res, log = build(["--letter", fixture("letter-nl.json"), "--facts", FACTS, "--jd", fixture(j["jd"]), "--out", pdf])
            good = code == 0 and res and res.get("pages") == 1
            rows.append(("NL", "Cover letter PDF", "PASS" if good else "FAIL", f"{res.get('pages')} page, {res.get('words')} words incl. header"))
            ok &= bool(good)

    rep, _ = truth_check.run(FACTS, cv=fixture("cv-nl-invented-number.json"))
    bad_fail = bool(rep.errors)
    code, _, _ = build([fixture("cv-nl-invented-number.json"), "--facts", FACTS, "--out", os.path.join(OUT, "BAD.pdf")])
    rows.append(("NL", "Invented number (91% -> 98%)", "PASS" if bad_fail and code == 1 else "FAIL",
                 f"check FAILED as expected: {rep.errors[0]['msg'] if rep.errors else '-'}; build refused (exit {code})"))
    ok &= bad_fail and code == 1

    if shutil.which("pdftoppm"):
        for f in os.listdir(OUT):
            if f.endswith(".pdf"):
                subprocess.run(["pdftoppm", "-r", "70", "-png", "-f", "1", "-l", "1", os.path.join(OUT, f),
                                os.path.join(OUT, "preview_" + f[:-4])], check=False)

    lines = ["# Kairo flow run (fake user Priya Sharma)", "", f"Run date: {date.today().isoformat()} (scan date fixed at {TODAY})", "",
             "| Job | Step | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d.replace('|', '/')} |" for a, b, c, d in rows]
    lines += ["", f"Overall: {'PASS' if ok else 'FAIL'}"]
    with open(os.path.join(OUTPUT, "flow-summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
