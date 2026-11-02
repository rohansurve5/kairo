#!/usr/bin/env python3
"""Kairo JD scan: signals a script can find reliably in a job description, plus a baseline fit score.

Claude reads the full JD and makes the final call (score +/-15, verdict, reasons). This script only
finds signals: years asked, required languages, salary range, visa / sponsorship wording, "local
candidates only", work mode, contract roles, agency posts, notice period, posting age, requirement
lines, and a baseline score from the user's "Strengths for fit scoring" table in my-facts.

Usage
  python3 jd_scan.py --facts my-facts.md --jd jd.txt --country NL [--title "..."] [--company "..."]
                     [--city "..."] [--posted 2026-10-28] [--source company_site|linkedin|naukri|indeed|other]
                     [--today 2026-11-02] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kairo_lib import (  # noqa: E402
    country_code, country_name, convert, fold, format_money, load_facts, needs_visa, norm_space,
    parse_salary, read_text, title_key,
)

# ---------------------------------------------------------------- years asked

EXP_RE = re.compile(r"(\d{1,2})\s*(\+|plus)?\s*(?:(?:-|–|—|to)\s*(\d{1,2})\s*\+?)?\s*(?:years?|yrs?)\b", re.I)


def parse_experience(text):
    found = []
    for m in EXP_RE.finditer(text or ""):
        before = text[max(0, m.start() - 40): m.start()]
        after = text[m.end(): m.end() + 70]
        if re.search(r"(for|over|than|past|last|nearly|almost|since|across)\s*$", before, re.I) and not re.search(
                r"experien", after[:25], re.I):
            continue
        if re.match(r"^\s*(ago|old|of (history|innovation|heritage|growth|success)|in business)", after, re.I):
            continue
        req_after = re.match(
            r"^[^.\n]{0,60}(experien|in (a |an )?(product|pm|similar|b2b|saas|tech|software|fintech|payments|the field|a similar)"
            r"|of (product|pm|relevant|professional|hands-on|managing|building|leading|working|industry)|working|managing|leading|building|as a)",
            after, re.I)
        req_before = re.search(r"(experience|minimum|at least|min\.?|requires?|with)[^.\n]{0,15}$", before, re.I)
        if not req_after and not req_before:
            continue
        lo = int(m.group(1))
        hi = int(m.group(3)) if m.group(3) else None
        if lo > 25 or (hi is not None and hi < lo):
            continue
        found.append({"min": lo, "max": hi, "text": m.group(0).strip()})
    if not found:
        return None
    main = max(found, key=lambda f: f["min"])
    return {"min": main["min"], "max": main["max"], "text": ", ".join(f["text"] for f in found[:3])}


# ---------------------------------------------------------------- languages

LANGS = ["dutch", "german", "french", "polish", "italian", "spanish", "portuguese", "swedish", "danish", "norwegian",
         "finnish", "czech", "arabic", "mandarin", "chinese", "cantonese", "malay", "bahasa", "japanese", "korean",
         "hindi", "marathi", "tamil", "telugu", "kannada", "bengali", "gujarati", "russian", "turkish", "hebrew"]
REQ = re.compile(r"(fluen|native|proficien|excellent|strong|business[- ]level|professional|mother tongue|must|required|"
                 r"mandatory|essential|\bc1\b|\bc2\b|\bb2\b|full professional|written and spoken|spoken and written)", re.I)
OPTIONAL = re.compile(r"(plus|nice[- ]to[- ]have|bonus|advantage|preferred|desirable|beneficial|not required|not necessary|"
                      r"no need|helpful|asset|welcome|optional|appreciated|would be great)", re.I)
LEVEL_RANK = {"a1": 1, "a2": 2, "basic": 1, "b1": 3, "intermediate": 3, "b2": 4, "c1": 5, "professional": 5,
              "advanced": 5, "c2": 6, "fluent": 6, "native": 7, "mother tongue": 7, "bilingual": 7}


def level_rank(level):
    lv = fold(level or "")
    for k, v in sorted(LEVEL_RANK.items(), key=lambda kv: -len(kv[0])):
        if k in lv:
            return v
    return 0


def language_check(text, user_langs):
    out = []
    for s in re.split(r"(?<=[.!?•])\s+|\n+", text or ""):
        for lang in LANGS:
            if not re.search(rf"\b{lang}\b", s, re.I):
                continue
            if re.search(r"(company|team|office|market|customers?|startup|based|headquarter|law|bank)", s, re.I) and not REQ.search(s):
                continue
            if REQ.search(s) and not OPTIONAL.search(s):
                have = user_langs.get(lang)
                if have is not None and level_rank(have) >= 4:
                    continue
                if not any(o["lang"] == lang for o in out):
                    out.append({"lang": lang.capitalize(), "you_have": have or "", "snippet": norm_space(s)[:200]})
    for o in out:
        o["lang"] = o["lang"].capitalize()
    return out


def jd_language(text):
    words = re.findall(r"[a-zà-ž]+", (text or "").lower())
    if len(words) < 80:
        return "en"
    sets = {
        "English": ["the", "and", "you", "with", "for", "our", "will", "are", "to", "of"],
        "German": ["und", "der", "die", "das", "wir", "sie", "mit", "für", "ist", "auf", "ein", "eine"],
        "French": ["et", "les", "des", "nous", "vous", "pour", "avec", "une", "dans", "est", "sur"],
        "Dutch": ["en", "het", "van", "wij", "je", "voor", "met", "een", "jij", "ons", "bij", "naar"],
        "Polish": ["i", "w", "z", "oraz", "się", "dla", "na", "jest", "do", "nie"],
    }
    scores = {k: sum(1 for w in words if w in v) / len(words) for k, v in sets.items()}
    best = max(scores, key=scores.get)
    return "en" if best == "English" else best


# ---------------------------------------------------------------- visa / sponsorship

COUNTRY_WORDS = r"(?:the )?(?:eu|eea|european union|netherlands|ireland|germany|france|poland|singapore|uae|united arab emirates|uk|united kingdom|india|us|usa|united states)"
SPONSOR_NO = re.compile(
    r"(unable|not able|cannot|can ?not|can't|do not|don't|won't|will not|are not able to|no)\s+(?:currently\s+)?"
    r"(?:offer|provide|support|sponsor)[^.]{0,40}(sponsor|visa|work permit)"
    r"|(?:visa\s+)?sponsorship (?:is )?not (?:available|offered|provided|possible)"
    r"|without (?:the need for |requiring )?(?:visa )?sponsorship"
    r"|must (?:already )?(?:have|hold|possess)[^.]{0,50}(right to work|work permit|work authori[sz]ation|eligib|residence visa|work visa)"
    r"|(?:valid|existing) (?:eu )?work permit (?:is )?required"
    r"|(?:already )?(?:eligible|authori[sz]ed|right) to work in " + COUNTRY_WORDS + r"[^.]{0,30}(?:required|is a must|without)",
    re.I)
SPONSOR_YES = re.compile(
    r"visa sponsorship|sponsor(?:ship)? (?:of )?(?:your |a |the )?(?:work )?(?:visa|permit)|relocation (?:support|package|assistance|budget|bonus)"
    r"|help (?:you )?relocat|we (?:can |will |do )?(?:offer|provide|support)[^.]{0,40}(?:visa|relocation)|highly skilled migrant"
    r"|kennismigrant|30% ruling|blue card|(?:employment|residence|work) visa (?:is )?(?:provided|sponsored|included|covered)"
    r"|visa (?:provided|included|covered|support)|employment pass (?:sponsor|support|provided)|skilled worker visa"
    r"|certificate of sponsorship|critical skills (?:employment )?permit|recognised sponsor|recognized sponsor",
    re.I)
NEGATION = re.compile(r"\b(not|no|unable|cannot|can't|can ?not|don't|do not|won't|will not|without|isn't|is not|aren't)\b", re.I)
LOCAL_ONLY = re.compile(
    r"must already (?:hold|have|possess)[^.]{0,40}(?:work permit|right to work|work authori[sz]ation|residence visa|work visa|residency)"
    r"|(?:already|currently) hold(?:s|ing)?(?: a)?(?: valid)? (?:[a-z]{2,5} )?(?:work permit|right to work|residence visa|work visa)"
    r"|local candidates only|only (?:considering |accepting |open to |hiring )?local (?:candidates|applicants)"
    r"|(?:not|n't)(?: currently)?(?: set up to)? hir(?:e|ing) in your location"
    r"|(?:eu|eea|uae|emirati|singapore(?:an)?|uk) (?:citizens|nationals|residents)(?: and [a-z ]{3,30})? only"
    r"|citizens or permanent residents only",
    re.I)


def _clause(text, start, end):
    s = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), start - 60)
    tail = re.search(r"[.\n;,]|\band\b", text[end:end + 40])
    e = end + (tail.start() if tail else 40)
    return text[s + 1:e]


def _snip(text, m, pad=60):
    return norm_space(text[max(0, m.start() - pad): m.end() + pad])


def sponsorship(text, remote_job=False):
    def sentence(m):
        s = max(text.rfind(".", 0, m.start()), text.rfind("\n", 0, m.start()))
        e = re.search(r"[.\n]", text[m.end():])
        return text[s + 1: m.end() + (e.start() if e else len(text))]

    def applies(m):  # "we can't sponsor visas for remote roles" does not apply to an office job
        return remote_job or "remote" not in sentence(m).lower()

    yes_all = list(SPONSOR_YES.finditer(text))
    positive = [m for m in yes_all if not NEGATION.search(_clause(text, m.start(), m.end()))]
    negated_yes = [m for m in yes_all if m not in positive and applies(m)]
    nos = [m for m in SPONSOR_NO.finditer(text) if applies(m)]
    if positive and (nos or negated_yes):
        return {"value": "mixed", "quote": _snip(text, positive[0]),
                "other_quote": _snip(text, (nos or negated_yes)[0])}
    if nos or negated_yes:
        return {"value": "no", "quote": _snip(text, (nos or negated_yes)[0])}
    if positive:
        if re.search(r"no relocation", text, re.I):
            return {"value": "mixed", "quote": _snip(text, positive[0]), "other_quote": "no relocation"}
        return {"value": "yes", "quote": _snip(text, positive[0])}
    return {"value": "unknown", "quote": ""}


# ---------------------------------------------------------------- other signals

CONTRACT = re.compile(r"\b(fixed[- ]term|contract(?:or)? (?:role|position|basis)|freelance|temporary (?:role|position|contract)|"
                      r"maternity cover|parental leave cover|\d{1,2}[- ]month contract|interim (?:role|position))\b", re.I)
AGENCY = re.compile(r"\b(our client|on behalf of (?:our|a) client|we are recruiting for|recruitment (?:agency|partner)|"
                    r"staffing (?:agency|firm)|confidential (?:company|client)|leading (?:mnc|company) in)\b", re.I)
SPECIALISED = re.compile(r"fraud|transaction monitoring|\bsearch\b|\branking\b|machine learning|\bml\b|data platform|"
                         r"data infrastructure|\bfx\b|foreign exchange|\bidentity\b|\bkyc\b|\baml\b|trust (?:&|and) safety|"
                         r"\brisk\b|ad[- ]?tech|card issuing|treasury|crypto|digital assets|quant|hardware|firmware|"
                         r"medical device|clinical|semiconductor", re.I)
SENIORITY = [("intern", r"\bintern(ship)?\b|\btrainee\b|\bapprentice\b"), ("junior", r"\bjunior\b|\bjr\.?\b|\bentry[- ]level\b|\bgraduate\b"),
             ("associate", r"\bassociate\b"), ("senior", r"\bsenior\b|\bsr\.?\b"), ("lead", r"\blead\b"),
             ("staff", r"\bstaff\b"), ("principal", r"\bprincipal\b"), ("head", r"\bhead of\b|\bhead\b"),
             ("director", r"\bdirector\b"), ("vp", r"\bvp\b|vice president"), ("chief", r"\bchief\b|\bc[pt]o\b")]
SENIOR_WORDS = r"\b(senior|sr|junior|jr|lead|principal|staff|associate|head|director|vp|intern|mid|level|i|ii|iii|iv)\b"
REQ_HEAD = re.compile(r"(requirement|qualification|what you('| wi)ll bring|what you bring|what we('re| are) looking for|"
                      r"you have|must[- ]haves?|who you are|about you|your profile|skills|experience you|you bring)", re.I)


def seniority(title):
    t = title or ""
    for name, pat in SENIORITY:
        if re.search(pat, t, re.I):
            return name
    return "mid"


def core_words(title):
    t = re.sub(SENIOR_WORDS, " ", title_key(title))
    t = re.sub(r"\b(of|and|the|for|in|at|to|a|an|with)\b", " ", t)
    return set(t.split())


def title_match(title, roles):
    tw = core_words(title)
    for r in roles:
        rw = core_words(r)
        if rw and rw <= tw:
            return r
    return None


def work_mode(text):
    if re.search(r"\bhybrid\b", text, re.I):
        return "hybrid"
    if re.search(r"fully remote|100% remote|remote[- ]first|\bremote\b(?! (?:sensing|control))", text, re.I):
        return "remote"
    if re.search(r"on-?site|in-office|in office|from (our|the) office|work from office", text, re.I):
        return "onsite"
    return "unknown"


def remote_scope(text, home_country):
    home = fold(country_name(home_country))
    m = re.search(r"remote (?:within|in|from|across) (?:the )?([A-Z][A-Za-z ]{1,30}?)(?: only)?[.,;\n)]", text) or re.search(
        r"(?:must|need to|should) (?:be )?(?:based|located|living|resid\w*) in (?:the )?([A-Z][A-Za-z ]{1,30}?)[.,;\n)]", text)
    if not m:
        return None
    place = fold(m.group(1))
    if home and home in place or re.search(r"anywhere|worldwide|global", place):
        return None
    if re.search(r"(candidates?|applicants?|people|hire|hiring|work)[^.]{0,60}\b(" + re.escape(home) + r"|anywhere in the world|any country|worldwide|globally)\b", fold(text)):
        return None
    return norm_space(m.group(0))[:160]


def notice_days(text):
    t = fold(text)
    if not t:
        return None
    if re.search(r"immediate|\b0 days\b|\bnone\b", t):
        return 0
    m = re.search(r"(\d+)\s*(day|week|month)", t)
    if not m:
        return None
    n = int(m.group(1))
    return n * {"day": 1, "week": 7, "month": 30}[m.group(2)]


def jd_notice(text):
    t = text or ""
    if re.search(r"immediate join|join(ing)? immediately|immediate start|start immediately|immediate joiner", t, re.I):
        return {"max_days": 15, "text": "immediate joiners"}
    m = re.search(r"notice period (?:of )?(?:up to |max(?:imum)? |less than |within |under )?(\d+)\s*days", t, re.I) or re.search(
        r"(\d+)\s*days(?:'|’)? notice", t, re.I)
    if m:
        return {"max_days": int(m.group(1)), "text": norm_space(m.group(0))}
    return None


def posted_from_text(text, today):
    m = re.search(r"(\d+)\+?\s*(day|week|month)s?\s+ago", text or "", re.I)
    if m:
        n = int(m.group(1)) * {"day": 1, "week": 7, "month": 30}[m.group(2).lower()]
        return (today - timedelta(days=n)).isoformat()
    m = re.search(r"posted(?: on)?:?\s*(\d{4}-\d{2}-\d{2}|\d{1,2} [A-Za-z]{3,9} \d{4})", text or "", re.I)
    if m:
        for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(m.group(1), fmt).date().isoformat()
            except ValueError:
                pass
    return None


BULLET_MARK = re.compile(r"^(?:[-*•▪●]\s*|\d{1,2}[.)]\s+)")


def requirement_lines(text, limit=15):
    """Lines under a 'Requirements' / 'What you bring' style heading, until the next heading."""
    out, on = [], False
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        is_bullet = bool(BULLET_MARK.match(s))
        looks_heading = not is_bullet and len(s) < 60 and not s.endswith((".", ";", ",")) and len(s.split()) <= 8
        if looks_heading:
            on = bool(REQ_HEAD.search(s))
            continue
        if on:
            out.append(BULLET_MARK.sub("", s))
            if len(out) >= limit:
                break
    return out


def kw_count(hay, kw):
    k = kw.strip()
    if not k:
        return 0
    return len(re.findall(r"(?<![A-Za-z0-9])" + re.escape(k) + r"(?![A-Za-z0-9])", hay, re.I))


def baseline_score(title, text, facts, exp):
    hay = f"{title}\n{title}\n{text}"
    areas = []
    for s in facts["strengths"]:
        hits = sum(kw_count(hay, k) for k in s["keywords"])
        if hits:
            areas.append({"area": s["area"], "hits": hits, "points": round(s["weight"] * min(hits, 3) / 3, 1)})
    areas.sort(key=lambda a: -a["points"])
    skill_pts = min(52.0, sum(a["points"] for a in areas) * 0.85)
    title_pts = 0
    if title_match(title, facts["target_roles"]):
        title_pts += 6
    if any(kw_count(title, k) for s in facts["strengths"] for k in s["keywords"]):
        title_pts += 6
    title_pts = min(title_pts, 10)
    years = facts.get("years")
    exp_pts = 4
    if exp and years is not None:
        if exp["min"] > years:
            exp_pts = 0
        elif exp.get("max") is not None and exp["max"] + 4 < years:
            exp_pts = 4
        else:
            exp_pts = 8
    score = round(max(0, min(100, 30 + skill_pts + title_pts + exp_pts)))
    return {"score": score, "areas": areas[:8], "skill_points": round(skill_pts, 1), "title_points": title_pts,
            "experience_points": exp_pts}


# ---------------------------------------------------------------- main scan

def flag(code, severity, text, public_text):
    return {"code": code, "severity": severity, "text": text, "public_text": public_text}


def scan(facts, jd, country, title="", company="", city="", posted=None, source="other", today=None):
    today = today or date.today()
    code = country_code(country) or facts.get("home_country", "")
    home = facts.get("home_country", "")
    visa_needed = needs_visa(facts, code)
    flags = []
    title = title or ""

    exp = parse_experience(jd)
    yrs = facts.get("years")
    if exp and yrs is not None:
        if exp["min"] > yrs:
            sev = "block" if exp["min"] - yrs >= 3 else "warn"
            flags.append(flag("years_above", sev, f"Asks {exp['text']}; you have {yrs:g} years",
                              "Asks more years of experience than you have"))
        elif exp.get("max") is not None and exp["max"] + 4 < yrs:
            flags.append(flag("years_below", "warn", f"Asks {exp['text']}; you have {yrs:g} years (may be junior for you)",
                              "Role may be junior for your experience"))

    langs = language_check(jd, facts.get("languages", {}))
    for lg in langs:
        flags.append(flag("language_required", "block", f"Requires {lg['lang']}: \"{lg['snippet'][:120]}\"",
                          f"Requires {lg['lang']}"))
    jl = jd_language(jd)
    if jl != "en":
        flags.append(flag("jd_not_english", "warn", f"The JD is written in {jl}: the job likely needs {jl}",
                          f"JD is written in {jl}"))

    sal = parse_salary(jd)
    row = facts["salary"].get(code)
    sal_note = None
    if sal and row:
        hi = convert(sal["max"], sal["currency"], sal["period"], row["currency"], row["period"])
        lo = convert(sal["min"], sal["currency"], sal["period"], row["currency"], row["period"])
        if hi is not None and row.get("minimum") and hi < row["minimum"]:
            flags.append(flag("salary_below_floor", "block",
                              f"Posted {sal['text']} is below your minimum ({format_money(row['minimum'], row['currency'], row['period'], code)})",
                              "Posted salary is below your minimum"))
        if lo is None:
            sal_note = f"posted in {sal['currency']}, your table uses {row['currency']}"

    mode = work_mode(jd)
    sp = sponsorship(jd, remote_job=(mode == "remote"))
    local = LOCAL_ONLY.search(jd)
    if visa_needed:
        if local:
            flags.append(flag("local_only", "block", f"Local candidates only: \"{_snip(jd, local, 40)}\"", "Local candidates only"))
        if sp["value"] == "no":
            flags.append(flag("no_sponsorship", "block", f"No visa sponsorship: \"{sp['quote']}\"", "JD says no visa sponsorship"))
        elif sp["value"] in ("unknown", "mixed"):
            flags.append(flag("visa_unknown", "warn",
                              "JD is unclear on visa sponsorship: run the visa check" if sp["value"] == "mixed"
                              else "JD does not mention visa sponsorship: run the visa check",
                              "Visa sponsorship not confirmed"))
    scope = remote_scope(jd, home) if mode == "remote" else None
    if scope and code != home:
        flags.append(flag("remote_region", "block" if visa_needed else "warn",
                          f"Remote, but limited to a region: \"{scope}\"", "Remote role limited to another region"))
    if facts["target_countries"] and code and code not in facts["target_countries"]:
        flags.append(flag("location_not_target", "warn", f"{country_name(code)} is not in your target countries",
                          "Not in your target countries"))

    sen = seniority(title)
    target_sens = {seniority(r) for r in facts["target_roles"]} or {"mid"}
    if sen in ("head", "director", "vp", "chief", "principal", "staff") and sen not in target_sens:
        flags.append(flag("seniority_mismatch", "warn", f"Title level '{sen}' is above your target roles",
                          "Seniority above your targets"))
    if sen in ("intern", "junior", "associate") and sen not in target_sens:
        flags.append(flag("seniority_mismatch", "warn", f"Title level '{sen}' is below your target roles",
                          "Seniority below your targets"))
    tm = title_match(title, facts["target_roles"]) if title else None
    if title and facts["target_roles"] and not tm:
        flags.append(flag("title_mismatch", "warn", f"\"{title}\" does not match your target roles",
                          "Title differs from your target roles"))
    sp_dom = SPECIALISED.search(title)
    if sp_dom:
        covered = any(fold(sp_dom.group(0)) in fold(" ".join([s["area"]] + s["keywords"])) for s in facts["strengths"])
        if not covered:
            flags.append(flag("specialised_domain", "warn",
                              f"Specialised domain in the title ({sp_dom.group(0)}): only apply if your facts cover it",
                              "Specialised domain"))
    con = CONTRACT.search(jd)
    if con:
        flags.append(flag("contract_role", "warn", f"Contract / fixed-term role: \"{_snip(jd, con, 30)}\""
                          + (" (often can't support a work visa)" if visa_needed else ""), "Contract or fixed-term role"))
    ag = AGENCY.search(jd)
    if ag:
        flags.append(flag("agency_post", "warn", f"Posted by an agency, employer not named: \"{_snip(jd, ag, 30)}\"",
                          "Employer not named (agency post)"))

    jn = jd_notice(jd)
    yn = notice_days(facts.get("notice", ""))
    if jn and yn is not None and yn > jn["max_days"]:
        flags.append(flag("notice_too_long", "warn", f"JD wants {jn['text']}; your notice is {facts.get('notice')}",
                          "Your notice period is longer than the JD wants"))

    posted_at = posted or posted_from_text(jd, today)
    age = None
    if posted_at:
        try:
            age = (today - date.fromisoformat(posted_at)).days
        except ValueError:
            age = None
    if age is not None:
        company_page = source in ("company_site", "greenhouse", "lever", "workday", "ashby", "careers_page")
        limit = 30 if company_page else (21 if code == home else 10)
        if age > limit:
            flags.append(flag("stale_posting", "warn",
                              f"Posted {age} days ago (over {limit} for this source): may be filled or a repost; check the company's careers page",
                              "Posting may be old or a repost"))

    base = baseline_score(title, jd, facts, exp)
    return {
        "job": {"title": title, "company": company, "country": code, "country_name": country_name(code), "city": city,
                "source": source, "posted_at": posted_at, "age_days": age, "work_mode": mode, "seniority": sen,
                "matches_target_role": tm},
        "needs_visa": visa_needed,
        "signals": {"years": exp, "languages_required": langs, "jd_language": jl, "salary": sal, "salary_note": sal_note,
                    "sponsorship": sp, "local_only": _snip(jd, local, 40) if local else None,
                    "contract": _snip(jd, con, 30) if con else None, "agency": _snip(jd, ag, 30) if ag else None,
                    "remote_scope": scope, "notice": jn},
        "baseline": base,
        "score_floor": facts.get("score_floor", 60),
        "red_flags": flags,
        "requirements": requirement_lines(jd),
    }


def print_text(r):
    j = r["job"]
    print(f"Kairo JD scan: {j['title'] or '(no title)'} | {j['company'] or '?'} | {j['country_name']}"
          f"{' | ' + j['city'] if j['city'] else ''}")
    b = r["baseline"]
    print(f"  baseline score: {b['score']} (floor {r['score_floor']}); areas: "
          + (", ".join(f"{a['area']} x{a['hits']}" for a in b["areas"]) or "none matched"))
    s = r["signals"]
    print(f"  work mode: {j['work_mode']} | level: {j['seniority']} | needs visa here: {r['needs_visa']}")
    print(f"  years asked: {s['years']['text'] if s['years'] else 'not stated'}")
    print(f"  salary: {s['salary']['text'] + ' (' + s['salary']['currency'] + '/' + s['salary']['period'] + ')' if s['salary'] else 'not stated'}"
          + (f" [{s['salary_note']}]" if s["salary_note"] else ""))
    print(f"  sponsorship wording: {s['sponsorship']['value']}" + (f" \"{s['sponsorship']['quote']}\"" if s['sponsorship']['quote'] else ""))
    print(f"  posted: {j['posted_at'] or 'unknown'}" + (f" ({j['age_days']} days ago)" if j["age_days"] is not None else ""))
    if r["red_flags"]:
        print("  red flags:")
        for f in r["red_flags"]:
            print(f"    [{f['severity']}] {f['code']}: {f['text']}")
    else:
        print("  red flags: none found by the script (still read the JD)")
    if r["requirements"]:
        print("  requirement lines (check each against my-facts):")
        for ln in r["requirements"]:
            print(f"    - {ln[:160]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kairo JD scan")
    ap.add_argument("--facts", required=True)
    ap.add_argument("--jd", required=True, help="job description text file")
    ap.add_argument("--country", required=True, help="job country code, e.g. IN, NL, AE, GB")
    ap.add_argument("--title", default="")
    ap.add_argument("--company", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--posted", help="posting date YYYY-MM-DD if known")
    ap.add_argument("--source", default="other")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        facts = load_facts(a.facts)
        jd = read_text(a.jd)
    except OSError as exc:
        print(f"Kairo JD scan: cannot read input: {exc}", file=sys.stderr)
        return 2
    today = date.fromisoformat(a.today) if a.today else date.today()
    r = scan(facts, jd, a.country, a.title, a.company, a.city, a.posted, a.source, today)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print_text(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
