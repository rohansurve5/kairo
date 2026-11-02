#!/usr/bin/env python3
"""Kairo truth check. Every fact in a CV, cover letter or form answers must come from my-facts.md.

Checks
  * every number exists in my-facts (a CV bullet's numbers must come from that same job/project);
    cover letter and answers may also use numbers from the job description (JD)
  * every company, job title and date range on the CV matches my-facts exactly
  * capitalised names / tools / clients exist in my-facts (or the JD, for letter and answers)
  * skills, education, certifications, languages and levels come from my-facts
  * "Never claim" lines from my-facts and generic fluff words are absent
  * word limits, and the share of CV bullets that carry a number
  * country rules: photo / date of birth only where allowed, CEFR levels for Germany

Usage
  python3 truth_check.py --facts my-facts.md --cv cv.json [--letter letter.json]
                         [--answers answers.json] [--jd jd.txt] [--json]
  python3 truth_check.py --facts my-facts.md --lint
Exit codes: 0 = PASS (warnings allowed), 1 = FAIL, 2 = bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kairo_lib import (  # noqa: E402
    COUNTRIES, capitalised_names, country_code, date_key, find_job, fold, load_facts, load_json,
    needs_visa, norm_space, number_tokens, number_values, parse_languages, read_text, title_key, word_count,
)

DEFAULT_LIMITS = {
    "cv_words_min": 300,
    "cv_words_max": 750,
    "summary_words_max": 60,
    "letter_words_max": 250,
    "answer_words_max": 80,
    "bullet_words_max": 40,
    "numbers_pct_min": 40,
}
GENERIC_FLUFF = [
    r"spearhead\w*", r"leverag(?:e|ed|es|ing)\b", r"synerg(?:y|ies|istic)", r"passionate", r"results[- ]driven",
    r"results[- ]oriented", r"\bdynamic\b", r"go[- ]getter", r"self[- ]starter", r"rock ?star", r"\bninja\b",
    r"\bguru\b", r"thought leader\w*", r"team player", r"detail[- ]oriented", r"hard[- ]?working",
    r"think(?:ing)? outside the box", r"proven track record", r"best[- ]in[- ]class", r"world[- ]class",
    r"cutting[- ]edge", r"game[- ]changer", r"i am (?:so |really )?excited to apply",
    r"i believe i (?:would|will) be a (?:great|perfect|good|strong) fit", r"to whom it may concern",
]
SALARY_WORDS = re.compile(r"\b(ctc|salary|salaries|lpa|expected pay|current pay|package of)\b", re.I)
CEFR = re.compile(r"^(a1|a2|b1|b2|c1|c2|native|mother tongue|bilingual)\b", re.I)
PHOTO_OK = {"DE", "FR", "AE"}
DOB_OK = {"DE", "AE"}


class Report:
    def __init__(self):
        self.issues = []
        self.stats = {}

    def add(self, level, doc, where, msg):
        self.issues.append({"level": level, "doc": doc, "where": where, "msg": msg})

    def err(self, doc, where, msg):
        self.add("error", doc, where, msg)

    def warn(self, doc, where, msg):
        self.add("warn", doc, where, msg)

    @property
    def errors(self):
        return [i for i in self.issues if i["level"] == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i["level"] == "warn"]


def limits(facts):
    lim = dict(DEFAULT_LIMITS)
    r = facts.get("rules", {})
    m = re.findall(r"\d+", r.get("cv words", ""))
    if len(m) >= 2:
        lim["cv_words_min"], lim["cv_words_max"] = int(m[0]), int(m[1])
    for key, fact_key in (("summary_words_max", "summary words max"), ("letter_words_max", "cover letter words max"),
                          ("answer_words_max", "answer words max"), ("numbers_pct_min", "bullets with numbers min %"),
                          ("bullet_words_max", "bullet words max")):
        m = re.search(r"\d+", r.get(fact_key, ""))
        if m:
            lim[key] = int(m.group(0))
    return lim


def norm_contact(v):
    v = fold(v or "")
    v = re.sub(r"^(https?://)?(www\.)?", "", v).rstrip("/")
    return re.sub(r"[\s()\-.]", "", v)


# ---------------------------------------------------------------- shared checks

def check_numbers(rep, doc, where, text, allowed_vals, other_vals=None, other_label="another part of your facts"):
    for tok, vals in number_tokens(text):
        if vals & allowed_vals:
            continue
        if other_vals is not None and vals & other_vals:
            rep.err(doc, where, f'number "{tok}" belongs to {other_label}, not to this entry: never move results between jobs')
        else:
            rep.err(doc, where, f'number "{tok}" is not in your my-facts')


def check_names(rep, doc, where, text, allowed_text):
    low = fold(allowed_text)
    seen = set()
    for w in capitalised_names(text):
        if w in seen:
            continue
        seen.add(w)
        fw = fold(w)
        forms = {fw, fw[:-1] if fw.endswith("s") else fw, fw[:-2] if fw.endswith("es") else fw}
        if not any(f and f in low for f in forms):
            rep.err(doc, where, f'name/tool "{w}" is not in your my-facts')


def check_claims(rep, doc, where, text, facts):
    for n in facts["never"]:
        m = n["re"].search(text)
        if m:
            rep.err(doc, where, f'never-claim line matched: "{m.group(0)}" (my-facts: {n["label"]})')
    own = fold(facts.get("all_text", ""))
    for pat in GENERIC_FLUFF:
        m = re.search(pat, text, re.I)
        if m and fold(m.group(0)) not in own:
            rep.err(doc, where, f'fluff phrase "{m.group(0)}": say what was done and the result instead')


def check_identity(rep, doc, obj, facts):
    if obj.get("name") and fold(obj["name"]) != fold(facts["name"]):
        rep.err(doc, "header", f'name "{obj["name"]}" differs from my-facts "{facts["name"]}"')
    c = obj.get("contact", {}) or {}
    for key in ("email", "phone", "linkedin", "website"):
        v = c.get(key)
        if v and norm_contact(v) != norm_contact(facts.get(key, "")):
            rep.err(doc, "header", f"{key} \"{v}\" differs from my-facts")
    loc = c.get("location", "")
    if loc and facts.get("home_city") and fold(facts["home_city"]) not in fold(loc):
        rep.err(doc, "header", f'location "{loc}" must use your home city from my-facts ({facts["home_city"]})')


def has_number(text):
    return any(True for _ in number_tokens(text))


# ---------------------------------------------------------------- CV

def cv_plain_text(cv):
    parts = [cv.get("headline", ""), cv.get("summary", "")]
    for e in cv.get("experience", []):
        parts += [e.get("title", ""), e.get("company", ""), e.get("location", ""), e.get("dates", "")]
        parts += e.get("bullets", [])
    for p in cv.get("projects", []):
        parts += [p.get("name", ""), p.get("dates", "")] + p.get("bullets", []) + ([p["text"]] if p.get("text") else [])
    parts.append(", ".join(cv.get("skills", [])))
    parts += cv.get("education", []) + cv.get("certifications", []) + cv.get("languages", []) + cv.get("additional", [])
    return "\n".join(x for x in parts if x)


def match_line(line, candidates):
    """True if every number and capitalised word in line appears in one candidate line."""
    nums = number_values(line)
    words = {fold(w) for w in re.findall(r"[A-Za-z][A-Za-z0-9+.#&-]+", line) if w[0].isupper()}
    for c in candidates:
        cv_ = number_values(c)
        cf = fold(c)
        if nums <= cv_ and all(w in cf for w in words):
            return True
    return False


def check_cv(rep, cv, facts, lim):
    D = "CV"
    check_identity(rep, D, cv, facts)
    country = country_code(cv.get("country"))
    personal = cv.get("personal", {}) or {}
    opts = cv.get("options", {}) or {}
    if not country:
        rep.err(D, "country", 'cv.json needs "country" (e.g. "NL")')
    elif country not in COUNTRIES:
        rep.warn(D, "country", f"no format rules for {country}: a neutral format is used")
    if personal.get("nationality") and fold(personal["nationality"]) != fold(facts["nationality"]):
        rep.err(D, "header", f'nationality "{personal["nationality"]}" differs from my-facts')
    if personal.get("home_country") and country_code(personal["home_country"]) != facts["home_country"]:
        rep.err(D, "header", "home country differs from my-facts")
    if country and "needs_visa" in personal and personal["needs_visa"] is not None:
        want = needs_visa(facts, country)
        if bool(personal["needs_visa"]) != want:
            rep.err(D, "header", f"needs_visa={personal['needs_visa']} but my-facts visa needs for {country} say {want}")
    if opts.get("include_photo") or personal.get("photo"):
        if country not in PHOTO_OK:
            rep.err(D, "header", f"no photo on a CV for {country} (allowed only for {', '.join(sorted(PHOTO_OK))}, and off by default)")
        else:
            rep.warn(D, "header", f"photo is optional in {country}: check current advice")
    if opts.get("include_dob") or personal.get("date_of_birth"):
        if country not in DOB_OK:
            rep.err(D, "header", f"no date of birth on a CV for {country}")
        elif not facts.get("dob") or norm_space(str(personal.get("date_of_birth", ""))) != norm_space(facts["dob"]):
            rep.err(D, "header", "date of birth must match '- Date of birth:' in my-facts")
        else:
            rep.warn(D, "header", f"date of birth is optional in {country}: check current advice")

    # headline
    hl = cv.get("headline", "")
    title_part, _, tags_part = hl.partition("|")
    ok_titles = {title_key(t) for t in facts["headline_titles"]} | {title_key(j["title"]) for j in facts["jobs"]}
    if title_part.strip() and title_key(title_part) not in ok_titles:
        rep.err(D, "headline", f'headline title "{title_part.strip()}" is not in your Headline titles or past job titles')
    facts_low = fold(facts["name_text"])
    for tag in [t for t in re.split(r"\s*[·•,/]\s*", tags_part) if t.strip()]:
        missing = [w for w in re.findall(r"[A-Za-z0-9+#&]+", tag) if len(w) > 2 and fold(w) not in facts_low]
        if missing:
            rep.err(D, "headline", f'headline tag "{tag.strip()}" is not one of your real areas in my-facts')

    allowed_all = number_values(facts["number_text"])
    # summary
    s = cv.get("summary", "")
    if not s.strip():
        rep.warn(D, "summary", "no summary")
    if word_count(s) > lim["summary_words_max"]:
        rep.err(D, "summary", f"summary has {word_count(s)} words (max {lim['summary_words_max']})")
    check_numbers(rep, D, "summary", s, allowed_all)
    check_names(rep, D, "summary", s, facts["name_text"])

    # experience
    seen, bullets, numbered = set(), 0, 0
    for e in cv.get("experience", []):
        comp = e.get("company", "")
        where = f"{comp or '?'}"
        fj = find_job(facts, comp)
        if not fj:
            rep.err(D, where, f'company "{comp}" is not in your work history')
            own_vals = set()
        else:
            seen.add(id(fj))
            if title_key(e.get("title", "")) != title_key(fj["title"]):
                rep.err(D, where, f'title "{e.get("title")}" differs from my-facts "{fj["title"]}"')
            if date_key(e.get("dates", "")) != date_key(fj["dates"]):
                rep.err(D, where, f'dates "{e.get("dates")}" differ from my-facts "{fj["dates"]}"')
            if e.get("location") and fj.get("location") and fold(e["location"]) != fold(fj["location"]):
                rep.err(D, where, f'location "{e["location"]}" differs from my-facts "{fj["location"]}"')
            own_vals = number_values(fj["text"])
        if not e.get("bullets"):
            rep.err(D, where, "every job on the CV needs at least 1 bullet")
        for i, b in enumerate(e.get("bullets", []), 1):
            w = f"{where}, bullet {i}"
            bullets += 1
            numbered += 1 if has_number(b) else 0
            if word_count(b) > lim["bullet_words_max"]:
                rep.warn(D, w, f"bullet has {word_count(b)} words (aim for <= {lim['bullet_words_max']})")
            check_numbers(rep, D, w, b, own_vals, allowed_all)
            check_names(rep, D, w, b, facts["name_text"])
    for fj in facts["jobs"]:
        if id(fj) not in seen:
            rep.warn(D, "experience", f'job "{fj["title"]} | {fj["company"]}" is not on the CV (a gap the reader may ask about)')

    # projects
    for p in cv.get("projects", []):
        name = p.get("name", "")
        fp = next((x for x in facts["projects"] if fold(x["name"]) == fold(name)), None)
        if not fp:
            rep.err(D, f"project {name}", f'project "{name}" is not in your my-facts projects')
            own_vals = set()
        else:
            own_vals = number_values(fp["text"])
            if p.get("url") and fp.get("url") and p["url"].rstrip("/") != fp["url"].rstrip("/"):
                rep.err(D, f"project {name}", "project link differs from my-facts")
        lines = list(p.get("bullets", [])) + ([p["text"]] if p.get("text") else [])
        for i, b in enumerate(lines, 1):
            w = f"project {name}, line {i}"
            bullets += 1
            numbered += 1 if has_number(b) else 0
            check_numbers(rep, D, w, b, own_vals, allowed_all)
            check_names(rep, D, w, b, facts["name_text"])

    # skills
    ok_sk = {fold(x) for x in facts["skills"]} | set(facts["aliases"].keys()) | {fold(v) for v in facts["aliases"].values()}
    for sk in cv.get("skills", []):
        if fold(sk) not in ok_sk:
            rep.err(D, "skills", f'skill "{sk}" is not on your Skills list (or Skill aliases) in my-facts')

    # education, certifications, additional
    for line in cv.get("education", []):
        if not match_line(line, facts["education"]):
            rep.err(D, "education", f'"{line}" does not match an Education line in my-facts')
    for line in cv.get("certifications", []):
        if not match_line(line, facts["certifications"]):
            rep.err(D, "certifications", f'"{line}" does not match a Certification in my-facts')
    for line in cv.get("additional", []):
        check_numbers(rep, D, "additional", line, allowed_all)
        check_names(rep, D, "additional", line, facts["name_text"])

    # languages
    langs = parse_languages(", ".join(cv.get("languages", [])))
    for lang, level in langs.items():
        have = facts["languages"].get(lang)
        if have is None:
            rep.err(D, "languages", f'language "{lang}" is not in my-facts')
            continue
        if level and fold(level) != fold(have):
            rep.err(D, "languages", f'{lang} level "{level}" differs from my-facts "{have}"')
        if country == "DE" and not CEFR.match(level or have or ""):
            rep.err(D, "languages", f"Germany: give a CEFR level (A1-C2 or Native) for {lang} in my-facts")

    # whole-CV checks
    text = cv_plain_text(cv)
    check_claims(rep, D, "whole CV", text, facts)
    if SALARY_WORDS.search(text):
        rep.err(D, "whole CV", "salary / CTC never goes on a CV")
    wc = word_count(text)
    if wc > lim["cv_words_max"]:
        rep.err(D, "whole CV", f"CV has {wc} words (max {lim['cv_words_max']}): cut the least relevant bullets")
    elif wc < lim["cv_words_min"]:
        rep.warn(D, "whole CV", f"CV has {wc} words (aim for {lim['cv_words_min']}-{lim['cv_words_max']})")
    pct = round(100 * numbered / bullets) if bullets else 0
    if bullets and pct < lim["numbers_pct_min"]:
        fb = [b for j in facts["jobs"] for b in j["bullets"]] + [b for p in facts["projects"] for b in p["bullets"]]
        facts_pct = round(100 * sum(1 for b in fb if has_number(b)) / len(fb)) if fb else 0
        msg = f"{pct}% of bullets have a number (min {lim['numbers_pct_min']}%)"
        if facts_pct >= lim["numbers_pct_min"]:
            rep.err(D, "whole CV", msg + ": pick more bullets with real results from my-facts")
        else:
            rep.warn(D, "whole CV", msg + f"; only {facts_pct}% of your my-facts bullets have numbers: add real ones if you have them")
    rep.stats["cv"] = {"words": wc, "bullets": bullets, "bullets_with_numbers_pct": pct,
                       "summary_words": word_count(s), "country": country}


# ---------------------------------------------------------------- letter and answers

def check_letter(rep, L, facts, jd, lim):
    D = "Cover letter"
    check_identity(rep, D, L, facts)
    paras = L.get("paragraphs", [])
    body = "\n".join(paras)
    wc = word_count(body)
    if wc > lim["letter_words_max"]:
        rep.err(D, "body", f"cover letter has {wc} words (max {lim['letter_words_max']})")
    if not 3 <= len(paras) <= 5:
        rep.warn(D, "body", f"{len(paras)} paragraphs (aim for 3-4)")
    extra = "\n".join([jd, L.get("company", ""), L.get("role", "")])
    allowed = number_values(facts["number_text"] + "\n" + extra)
    for i, p in enumerate(paras, 1):
        check_numbers(rep, D, f"paragraph {i}", p, allowed)
        check_names(rep, D, f"paragraph {i}", p, facts["name_text"] + "\n" + extra)
    check_claims(rep, D, "body", body, facts)
    comp = L.get("company", "")
    if comp and fold(comp.split()[0]) not in fold(body):
        rep.warn(D, "body", f'the letter never names "{comp}": make it specific to them')
    if SALARY_WORDS.search(body):
        rep.warn(D, "body", "salary is for the form, not the cover letter (unless the job asks)")
    rep.stats["letter"] = {"words": wc, "paragraphs": len(paras)}


def check_answers(rep, A, facts, jd, lim):
    D = "Answers"
    extra = "\n".join([jd, A.get("company", ""), A.get("role", "")])
    allowed = number_values(facts["number_text"] + "\n" + facts["salary_text"] + "\n" + extra)
    items = A.get("answers", [])
    for i, qa in enumerate(items, 1):
        a = qa.get("a", "")
        w = f"answer {i} ({norm_space(qa.get('q', ''))[:40]})"
        if word_count(a) > lim["answer_words_max"]:
            rep.err(D, w, f"{word_count(a)} words (max {lim['answer_words_max']})")
        check_numbers(rep, D, w, a, allowed)
        check_names(rep, D, w, a, facts["name_text"] + "\n" + extra)
        check_claims(rep, D, w, a, facts)
    rep.stats["answers"] = {"count": len(items)}


# ---------------------------------------------------------------- main

def run(facts_path, cv=None, letter=None, answers=None, jd_path=None, lint=False):
    rep = Report()
    facts = load_facts(facts_path)
    for level, msg in facts["lint"]:
        rep.add(level, "my-facts", "file", msg)
    rep.stats["facts"] = {"jobs": len(facts["jobs"]), "projects": len(facts["projects"]), "skills": len(facts["skills"]),
                          "never_claim": len(facts["never"]), "salary_rows": len(facts["salary"]),
                          "strengths": len(facts["strengths"])}
    if lint:
        return rep, facts
    lim = limits(facts)
    jd = read_text(jd_path)
    if (letter or answers) and not jd:
        rep.warn("input", "JD", "no --jd given: numbers and names from the job description are not allowed")
    if cv:
        check_cv(rep, load_json(cv), facts, lim)
    if letter:
        check_letter(rep, load_json(letter), facts, jd, lim)
    if answers:
        check_answers(rep, load_json(answers), facts, jd, lim)
    return rep, facts


def print_report(rep, title="Kairo truth check"):
    res = "PASS" if not rep.errors else "FAIL"
    print(f"{title}: {res}  ({len(rep.errors)} problems, {len(rep.warnings)} warnings)")
    for i in rep.errors + rep.warnings:
        tag = "FAIL" if i["level"] == "error" else "warn"
        print(f"  {tag}  [{i['doc']} | {i['where']}] {i['msg']}")
    for k, v in rep.stats.items():
        print(f"  stats {k}: " + ", ".join(f"{a}={b}" for a, b in v.items()))
    if rep.errors:
        print("Fix every FAIL line using only my-facts (never edit my-facts or this script to pass), then run again.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kairo truth check")
    ap.add_argument("--facts", required=True, help="path to my-facts.md")
    ap.add_argument("--cv", help="cv.json")
    ap.add_argument("--letter", help="letter.json (cover letter)")
    ap.add_argument("--answers", help="answers.json (job-specific form answers)")
    ap.add_argument("--jd", help="job description text file")
    ap.add_argument("--lint", action="store_true", help="only check that my-facts.md is complete and readable")
    ap.add_argument("--json", action="store_true", help="print JSON")
    a = ap.parse_args(argv)
    if not (a.cv or a.letter or a.answers or a.lint):
        ap.error("give --cv, --letter, --answers or --lint")
    try:
        rep, _ = run(a.facts, a.cv, a.letter, a.answers, a.jd, a.lint)
    except (OSError, ValueError) as exc:
        print(f"Kairo truth check: cannot read input: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"result": "PASS" if not rep.errors else "FAIL", "errors": len(rep.errors),
                          "warnings": len(rep.warnings), "issues": rep.issues, "stats": rep.stats}, indent=2,
                         ensure_ascii=False))
    else:
        print_report(rep, "Kairo my-facts check" if a.lint else "Kairo truth check")
    return 0 if not rep.errors else 1


if __name__ == "__main__":
    sys.exit(main())
