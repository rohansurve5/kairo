#!/usr/bin/env python3
"""Kairo standard form answers for one job: contact, location, visa, notice, languages, salary.

Salary rule (salary_answer in kairo_lib.py):
  1. a number the user gave for this one job wins (--override);
  2. a posted range in the same currency gets an answer inside it, 40% up from the bottom
     (lower half), rounded, never below the user's minimum;
  3. otherwise the user's expected amount from the salary table in my-facts.

Usage
  python3 form_answers.py --facts my-facts.md --country NL [--jd jd.txt | --salary-text "EUR 70,000 - 80,000"]
                          [--company C] [--role R] [--city "Job city"] [--override "EUR 80,000"] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kairo_lib import (  # noqa: E402
    country_code, country_name, fold, format_money, load_facts, needs_visa, parse_salary, read_text, salary_answer,
)
from jd_scan import CONTRACT, SHIFT, TRAVEL, notice_days  # noqa: E402
from kairo_lib import PREF_LABELS  # noqa: E402


def _pref_row(facts, key, question, flags):
    """Yes/No from my-facts, or ASK THE USER (never assume a preference)."""
    v = facts.get(key)
    if v is None:
        ask = f"ASK THE USER: my-facts does not say if you are open to {PREF_LABELS[key]}. Never assume."
        flags.append(ask)
        return (question, ask)
    return (question, "Yes" if v else "No")


def build(facts, country, jd="", salary_text="", company="", role="", city="", override=None):
    code = country_code(country) or facts["home_country"]
    home = facts["home_country"]
    abroad = code != home
    rows = [("Full name", facts["name"]), ("Email", facts["email"])]
    if facts["phone"]:
        rows.append(("Phone", facts["phone"]))
    if facts["linkedin"]:
        rows.append(("LinkedIn", facts["linkedin"]))
    if facts["website"]:
        rows.append(("Website / portfolio", facts["website"]))

    loc = f"{facts['home_city']}, {country_name(home)}" if facts["home_city"] else country_name(home)
    other_city = bool(city) and fold(city) != fold(facts["home_city"])
    flags = []
    if facts["relocate"] is True and abroad:
        loc += " (open to relocation)"
    elif facts["relocate"] is True and other_city:
        loc += f" (open to relocating to {city})"
    rows.append(("Current location", loc))
    if abroad and facts["nationality"]:
        rows.append(("Nationality", facts["nationality"]))

    visa = needs_visa(facts, code)
    vtext = facts["visa"].get(code, {}).get("text", "")
    if abroad:
        rows.append((f"Authorised to work in {country_name(code)} without sponsorship?",
                     "No" + (f": {vtext}" if vtext else ", I need visa sponsorship") if visa else "Yes"))
        rows.append(("Will you need visa sponsorship?", "Yes" if visa else "No"))
        rows.append(_pref_row(facts, "relocate", "Willing to relocate?", flags))
    elif other_city:
        rows.append(_pref_row(facts, "relocate", "Willing to relocate?", flags))
    if CONTRACT.search(jd or ""):
        rows.append(_pref_row(facts, "contract_ok", "Open to a contract / fixed-term role?", flags))
    if SHIFT.search(jd or ""):
        rows.append(_pref_row(facts, "shifts_ok", "Open to shift or night work?", flags))
    if TRAVEL.search(jd or ""):
        rows.append(_pref_row(facts, "travel_ok", "Willing to travel?", flags))

    if facts["notice"]:
        rows.append(("Notice period / earliest start", facts["notice"]))
    else:
        ask = "ASK THE USER: my-facts has no notice period. Never assume a start date."
        rows.append(("Notice period / earliest start", ask))
        flags.append(ask)
    if facts["years"] is not None:
        rows.append(("Total experience", f"{facts['years']:g} years"))
    if facts["me"].get("languages"):
        rows.append(("Languages", facts["me"]["languages"]))

    posted = parse_salary(salary_text or "") or parse_salary(jd or "")
    row = facts["salary"].get(code)
    sal = None
    missing_money = [k for k in ("expected", "minimum") if not row or row.get(k) is None]
    if missing_money and not override:
        ask = (f"ASK THE USER: my-facts has no {' or '.join('ask' if k == 'expected' else 'floor' for k in missing_money)}"
               f" for {country_name(code)}. Never fill in a number.")
        rows.append(("Expected CTC" if code == "IN" else "Expected salary", ask))
        flags.append(ask)
        row = None
    if row or override:
        row = row or {"country": code, "currency": "", "period": ""}
        sal = salary_answer(row, posted, override)
        flags += sal["flags"]
        if code == "IN":
            if facts["current_ctc"]:
                rows.append(("Current CTC", facts["current_ctc"]))
            rows.append(("Expected CTC", f"{sal['text']} (negotiable)"))
            nd = notice_days(facts["notice"])
            if nd is not None:
                rows.append(("Notice period (days)", str(nd)))
        else:
            rows.append(("Expected salary", f"{sal['text']}, open to discuss for the right role"))
            if sal["value"] is not None:
                rows.append(("Expected salary (number only)", f"{int(round(sal['value'])):,}"))
            if row.get("minimum") and sal["basis"] != "override":
                rows.append(("Minimum salary (only if the form asks)",
                             format_money(row["minimum"], row["currency"], row["period"], code)))

    basis = ""
    if sal:
        if sal["basis"] == "override":
            basis = "Salary: the number you gave for this job."
        elif sal["basis"].startswith("range"):
            lo, hi = sal["range"]
            basis = (f"Salary basis: posted {format_money(lo, row['currency'], row['period'])} to "
                     f"{format_money(hi, row['currency'], row['period'])} -> 40% up the range -> {sal['text']}")
            if sal["basis"] == "range+minimum":
                basis += " (raised to your minimum)"
        else:
            basis = "Salary basis: no usable posted range, so your expected amount from my-facts."
    return {"country": code, "company": company, "role": role, "rows": rows, "salary": sal, "posted": posted,
            "basis": basis, "flags": flags}


def to_markdown(r):
    head = f"# Form answers: {r['role'] or 'role'}, {r['company'] or 'company'} ({country_name(r['country'])})"
    out = [head, "", "| Question | Answer |", "|---|---|"]
    for q, a in r["rows"]:
        out.append(f"| {q} | {str(a).replace('|', '/')} |")
    if r["basis"]:
        out += ["", r["basis"]]
    for f in r["flags"]:
        out.append(f"Note: {f}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kairo standard form answers")
    ap.add_argument("--facts", required=True)
    ap.add_argument("--country", required=True)
    ap.add_argument("--jd", help="job description text file (used to find the posted salary)")
    ap.add_argument("--salary-text", default="", help="posted salary text if not in the JD")
    ap.add_argument("--company", default="")
    ap.add_argument("--role", default="")
    ap.add_argument("--city", default="", help="job city (for the relocation line)")
    ap.add_argument("--override", help="salary the user gave for this one job")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        facts = load_facts(a.facts)
        jd = read_text(a.jd)
    except OSError as exc:
        print(f"Kairo form answers: cannot read input: {exc}", file=sys.stderr)
        return 2
    r = build(facts, a.country, jd, a.salary_text, a.company, a.role, a.city, a.override)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
    else:
        print(to_markdown(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
