#!/usr/bin/env python3
"""Kairo shared helpers: read my-facts.md, find numbers and names, parse salaries.

Standard library only (Python 3.8+). Used by truth_check.py, jd_scan.py,
form_answers.py and build_cv_pdf.py. Nothing here talks to the internet.
"""
from __future__ import annotations

import json
import re
import unicodedata

# ---------------------------------------------------------------- countries

COUNTRIES = {
    "IN": "India",
    "NL": "Netherlands",
    "IE": "Ireland",
    "DE": "Germany",
    "PL": "Poland",
    "FR": "France",
    "AE": "United Arab Emirates",
    "SG": "Singapore",
    "GB": "United Kingdom",
}
COUNTRY_ALIASES = {
    "UK": "GB", "ENGLAND": "GB", "UNITED KINGDOM": "GB", "BRITAIN": "GB", "GREAT BRITAIN": "GB",
    "UAE": "AE", "DUBAI": "AE", "ABU DHABI": "AE", "UNITED ARAB EMIRATES": "AE",
    "INDIA": "IN", "NETHERLANDS": "NL", "THE NETHERLANDS": "NL", "HOLLAND": "NL",
    "IRELAND": "IE", "GERMANY": "DE", "DEUTSCHLAND": "DE", "POLAND": "PL", "POLSKA": "PL",
    "FRANCE": "FR", "SINGAPORE": "SG",
}


def country_code(value: str | None) -> str:
    """'UK' -> 'GB', 'Netherlands' -> 'NL', 'nl' -> 'NL'. Unknown values come back upper-cased."""
    if not value:
        return ""
    v = str(value).strip().upper()
    if v in COUNTRIES:
        return v
    return COUNTRY_ALIASES.get(v, v)


def country_name(code: str) -> str:
    return COUNTRIES.get(country_code(code), code)


# ---------------------------------------------------------------- text helpers

URL_RE = re.compile(r"(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.]+)", re.I)


def strip_urls(text: str) -> str:
    return URL_RE.sub(" ", text or "")


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def fold(s: str) -> str:
    """Lower-case, accents removed, dashes unified, spaces collapsed."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[‐-―−]", "-", s)
    return norm_space(s).lower()


def word_count(s: str) -> int:
    return len(re.findall(r"[\w₹€$£][^\s]*", s or ""))


LEGAL_SUFFIX = re.compile(
    r"\b(private|pvt|limited|ltd|llp|llc|inc|incorporated|corp|corporation|co|company|gmbh|ag|se|"
    r"b ?v|n ?v|bv|nv|sa|sas|sarl|s ?a|sp ?z ?o ?o|spolka|plc|pte|fze|fzco|fz llc|dmcc|holding|holdings|group|the)\b"
)


def company_key(name: str) -> str:
    """'Kestrel Payments Pvt. Ltd.' -> 'kestrel payments'."""
    s = fold(name)
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9&+ ]", " ", s)
    s = LEGAL_SUFFIX.sub(" ", s)
    return norm_space(s)


def title_key(title: str) -> str:
    s = fold(title)
    s = s.replace("sr.", "senior").replace("sr ", "senior ").replace("jr.", "junior")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return norm_space(s)


DASHES = re.compile(r"\s*(?:-|–|—|to|until|till)\s*", re.I)
PRESENT = re.compile(r"^(present|current|now|today|ongoing|date)$", re.I)


def date_key(dates: str) -> str:
    """'04/2022 - Present' and '04/2022 – present' -> '04/2022|present'."""
    s = norm_space(dates)
    parts = [p for p in DASHES.split(s, maxsplit=1) if p is not None]
    parts = [norm_space(p) for p in parts if norm_space(p)]
    out = []
    for p in parts:
        out.append("present" if PRESENT.match(p) else fold(p))
    return "|".join(out)


# ---------------------------------------------------------------- numbers

UNIT_MULT = {
    "k": 1e3, "thousand": 1e3,
    "m": 1e6, "mn": 1e6, "million": 1e6, "millions": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9,
    "cr": 1e7, "crore": 1e7, "crores": 1e7,
    "l": 1e5, "lpa": 1e5, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "x": 1.0,
}
NUM_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?<![A-Za-z0-9][.,])(\d+(?:[.,]\d+)*)"
    r"(?:\s?(k|K|mn|M|m|bn|B|cr|Cr|crores?|lakhs?|lacs?|L|LPA|lpa|x|X|thousand|millions?|billion)(?![A-Za-z0-9]))?"
    r"(?![A-Za-z0-9])"
)


def _to_float(raw: str) -> float | None:
    s = raw
    if re.fullmatch(r"\d{1,3}(,\d{3})+", s) or re.fullmatch(r"\d{1,2}(,\d{2})+,\d{3}", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3}){2,}", s):
        s = s.replace(".", "")
    elif s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    if s.count(".") > 1:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def number_tokens(text: str):
    """Yield (token_text, {values}) for each number in text. URLs and emails are ignored.

    '55K' -> {55, 55000}; '1.2 Cr' -> {1.2, 12000000}; '38%' -> {38}; '04/2022' -> {4}, {2022}.
    """
    for m in NUM_RE.finditer(strip_urls(text)):
        v = _to_float(m.group(1))
        if v is None:
            continue
        vals = {round(v, 4)}
        unit = (m.group(2) or "").lower()
        if unit in UNIT_MULT and UNIT_MULT[unit] != 1.0:
            vals.add(round(v * UNIT_MULT[unit], 4))
        yield m.group(0).strip(), vals


def number_values(text: str) -> set:
    out = set()
    for _, vals in number_tokens(text):
        out |= vals
    return out


# ---------------------------------------------------------------- capitalised names

COMMON_WORDS = set(
    """I I'm I've I'd I'll A An The And Or But Nor So Yet In On At For With To Of By From As Into Over Under
    About After Before During Since Until Via Per Than Then Also Both Each Every All Any Some Most More Less
    My Our Your Their His Her Its We You It They He She This That These Those Who What When Where Why How
    Dear Hi Hello Hiring Team Re Kind Regards Best Sincerely Thank Thanks Yours Warm Mr Ms Mrs Mx Dr
    January February March April May June July August September October November December
    Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec Q1 Q2 Q3 Q4 H1 H2
    Monday Tuesday Wednesday Thursday Friday Saturday Sunday
    India Netherlands Ireland Germany Poland France Singapore Dubai UAE Emirates Arab United Kingdom UK
    Europe European EU Asia APAC EMEA GCC Gulf Middle East Pune Mumbai Bengaluru Bangalore Delhi NCR
    Amsterdam Dublin Berlin Munich Warsaw Krakow Paris London Abu Dhabi Rotterdam Utrecht Eindhoven
    Open Present CV Resume PDF Yes No OK""".split()
)
SENT_SPLIT = re.compile(r"(?<=[.!?;:•–—|])\s+|\n+")


def capitalised_names(text: str):
    """Capitalised words that are not the first word of a sentence (likely names, tools, clients)."""
    out = []
    for sentence in SENT_SPLIT.split(strip_urls(text or "")):
        words = sentence.split()
        for pos, w0 in enumerate(words):
            w = re.sub(r"^[^A-Za-z0-9]+", "", w0)
            w = re.sub(r"['’]s$", "", w)
            w = re.sub(r"[^A-Za-z0-9+#]+$", "", w)
            if len(w) < 2:
                continue
            inner_caps = bool(re.match(r"^[a-z]+[A-Z][A-Za-z0-9]*$", w))  # iDEAL, eBay, iPhone
            if not inner_caps and (pos == 0 or not re.match(r"^[A-Z][A-Za-z0-9+.#&/-]*$", w)):
                continue
            if w in COMMON_WORDS:
                continue
            out.append(w)
    return out


# ---------------------------------------------------------------- my-facts parsing

SECTION_RULES = [
    ("aliases", r"alias"),
    ("never", r"never|do not claim|don't claim|must avoid|banned"),
    ("salary", r"salary|\bctc\b|\bpay\b"),
    ("visa", r"visa|work permit|work authori"),
    ("headline", r"headline"),
    ("work", r"work history|experience|employment|\bjobs\b"),
    ("projects", r"project"),
    ("education", r"education|degree"),
    ("certifications", r"certif|licen|courses|training"),
    ("strengths", r"strength|scoring"),
    ("approved", r"approved|extra lines|stories"),
    ("rules", r"\brules\b|limits|settings"),
    ("skills", r"skill"),
    ("targets", r"target|looking for|goals"),
    ("me", r"^me\b|about me|contact|personal"),
]
FACT_NUMBER_SECTIONS = ("me", "headline", "work", "projects", "education", "certifications",
                        "skills", "aliases", "approved")
FACT_NAME_SECTIONS = FACT_NUMBER_SECTIONS + ("targets", "visa")
CONTACT_KEYS = ("phone", "mobile", "email", "e-mail", "linkedin", "website", "portfolio", "github",
                "url", "date of birth", "dob")
KV_RE = re.compile(r"^\s*[-*]\s*([^:]{1,60}?)\s*:\s*(.*?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*•]\s+(.*\S)\s*$")
DATE_LIKE = re.compile(r"(\d{4}|present|current|now)", re.I)


def _section_key(heading: str) -> str:
    h = fold(heading)
    for key, pat in SECTION_RULES:
        if re.search(pat, h):
            return key
    return "other:" + h


def _kv(lines) -> dict:
    out = {}
    for ln in lines:
        m = KV_RE.match(ln)
        if m:
            out[fold(m.group(1))] = m.group(2).strip()
    return out


def _bullets(lines) -> list:
    out = []
    for ln in lines:
        m = BULLET_RE.match(ln)
        if m and not ln.lstrip().startswith("<!--"):
            out.append(m.group(1).strip())
    return out


def _table_rows(lines) -> list:
    rows = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    if rows and rows[0] and fold(rows[0][0]) in ("country", "area", "code"):
        rows = rows[1:]
    return rows


def _split_skills(line: str) -> list:
    parts, depth, cur = [], 0, ""
    for ch in line:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [norm_space(p) for p in parts if norm_space(p)]


def _entries(lines) -> list:
    """### Title | Company | Location | Dates  (+ bullet lines) -> list of dict(raw, parts, bullets, text)."""
    entries, cur = [], None
    for ln in lines:
        if ln.startswith("### "):
            cur = {"raw": ln[4:].strip(), "parts": [p.strip() for p in ln[4:].split("|")], "bullets": [], "lines": []}
            entries.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
            m = BULLET_RE.match(ln)
            if m:
                cur["bullets"].append(m.group(1).strip())
    for e in entries:
        e["text"] = "\n".join([e["raw"]] + e["lines"])
    return entries


def _parse_never(line: str):
    """'"team of 20" — why' / '/regex/ — why' / 'Shark Tank' -> (compiled regex, label)."""
    s = line.strip()
    m = re.match(r"^/(.+)/([a-z]*)\s*(?:[—–-]+\s*(.*))?$", s)
    if m:
        try:
            return re.compile(m.group(1), re.I), m.group(3) or m.group(1)
        except re.error:
            pass
    m = re.match(r"^[\"“](.+?)[\"”]\s*(?:[—–-]+\s*(.*))?$", s)
    phrase = m.group(1) if m else re.split(r"\s+[—–]\s+|\s+-\s+", s, maxsplit=1)[0]
    phrase = phrase.strip()
    if not phrase:
        return None
    pat = r"\s+".join(re.escape(w) for w in phrase.split())
    return re.compile(r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])", re.I), s


def parse_unit(unit: str) -> tuple:
    """'EUR/year' -> ('EUR', 'year'); 'LPA' -> ('INR', 'lpa'); 'AED / month' -> ('AED', 'month')."""
    u = norm_space(unit).upper().replace(" ", "")
    if u in ("LPA", "INRLPA", "LAKH/YEAR", "LAKHS/YEAR", "LAKHSPERANNUM"):
        return "INR", "lpa"
    m = re.match(r"^([A-Z$€£₹]{1,4})(?:/|PER)?(YEAR|YR|ANNUM|PA|MONTH|MO|MTH|PM|HOUR|HR)?$", u)
    if not m:
        return u, ""
    cur = {"€": "EUR", "£": "GBP", "₹": "INR", "$": "USD", "S$": "SGD"}.get(m.group(1), m.group(1))
    per = m.group(2) or "YEAR"
    per = "month" if per in ("MONTH", "MO", "MTH", "PM") else "hour" if per in ("HOUR", "HR") else "year"
    return cur, per


def _money(cell: str):
    s = cell.replace(",", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|K|L|lakh|lakhs|LPA|lpa)?", s)
    if not m:
        return None
    v = float(m.group(1))
    if m.group(2) and m.group(2).lower() == "k":
        v *= 1000
    return v


def _needs_visa(text: str):
    t = fold(text)
    if not t:
        return None
    if re.match(r"^(not needed|no\b|none|not required|citizen|have right|already)", t):
        return False
    if re.match(r"^(needs?|yes|required|requires)", t):
        return True
    if re.search(r"not needed|no visa|citizen|right to work|already (have|hold)|permanent resident|eu passport", t):
        return False
    return True


def parse_facts(text: str) -> dict:
    """Read my-facts.md into a dict. Never raises on bad input; problems go to facts['lint']."""
    sections, order, cur = {}, [], None
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)  # template comments are not facts
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            cur = _section_key(line[3:])
            if cur not in sections:
                sections[cur] = []
                order.append(cur)
            continue
        if cur:
            sections[cur].append(line)
    f = {"sections": {k: "\n".join(v) for k, v in sections.items()}, "lint": []}

    me = _kv(sections.get("me", []))
    f["me"] = me
    f["name"] = me.get("name", "")
    f["email"] = me.get("email", "")
    f["phone"] = me.get("phone", "")
    f["linkedin"] = me.get("linkedin", "")
    f["website"] = me.get("website", "")
    f["home_city"] = me.get("home city", me.get("city", ""))
    f["home_country"] = country_code(me.get("home country", ""))
    f["nationality"] = me.get("nationality", "")
    f["notice"] = me.get("notice period", "")
    f["dob"] = me.get("date of birth", "")
    yrs = re.search(r"\d+(?:\.\d+)?", me.get("total experience (years)", me.get("total experience", "")))
    f["years"] = float(yrs.group(0)) if yrs else None
    f["languages"] = parse_languages(me.get("languages", ""))

    tg = _kv(sections.get("targets", []))
    f["targets"] = tg
    f["target_roles"] = _split_skills(tg.get("roles", ""))
    f["target_countries"] = [country_code(c) for c in _split_skills(tg.get("countries", ""))]
    f["relocate"] = fold(tg.get("open to relocation", "yes")).startswith(("y", "true", "open"))
    floor = re.search(r"\d+", tg.get("score floor", ""))
    f["score_floor"] = int(floor.group(0)) if floor else 60

    sal_lines = sections.get("salary", [])
    f["salary"] = {}
    for row in _table_rows(sal_lines):
        if len(row) < 4:
            continue
        code = country_code(row[0])
        cur, per = parse_unit(row[3])
        f["salary"][code] = {
            "country": code,
            "expected": _money(row[1]),
            "minimum": _money(row[2]),
            "unit": row[3],
            "currency": cur,
            "period": per,
            "note": row[4] if len(row) > 4 else "",
        }
    skv = _kv(sal_lines)
    f["current_ctc"] = skv.get("current ctc", skv.get("current ctc (india)", ""))

    f["visa"] = {}
    for k, v in _kv(sections.get("visa", [])).items():
        f["visa"][country_code(k)] = {"text": v, "needs": _needs_visa(v)}

    f["headline_titles"] = _bullets(sections.get("headline", []))

    jobs = []
    for e in _entries(sections.get("work", [])):
        p = e["parts"]
        job = {"title": p[0] if p else "", "company": p[1] if len(p) > 1 else "", "location": "", "dates": "",
               "bullets": e["bullets"], "text": e["text"]}
        rest = p[2:]
        if rest and DATE_LIKE.search(rest[-1]):
            job["dates"] = rest[-1]
            rest = rest[:-1]
        if rest:
            job["location"] = rest[0]
        jobs.append(job)
    f["jobs"] = jobs

    projects = []
    for e in _entries(sections.get("projects", [])):
        p = e["parts"]
        pr = {"name": p[0] if p else "", "url": "", "dates": "", "bullets": e["bullets"], "text": e["text"]}
        for part in p[1:]:
            if re.match(r"^(https?://|www\.)", part):
                pr["url"] = part
            elif DATE_LIKE.search(part):
                pr["dates"] = part
        projects.append(pr)
    f["projects"] = projects

    f["education"] = _bullets(sections.get("education", []))
    f["certifications"] = _bullets(sections.get("certifications", []))
    skills = []
    for b in _bullets(sections.get("skills", [])):
        skills.extend(_split_skills(b))
    f["skills"] = skills
    f["aliases"] = {}
    for b in _bullets(sections.get("aliases", [])):
        if "=" in b:
            left, right = b.split("=", 1)
            f["aliases"][fold(left)] = right.strip()

    strengths = []
    for row in _table_rows(sections.get("strengths", [])):
        if len(row) >= 3:
            w = re.search(r"\d+(?:\.\d+)?", row[1])
            kws = [k for k in _split_skills(row[2]) if k]
            if w and kws:
                strengths.append({"area": row[0], "weight": float(w.group(0)), "keywords": kws})
    f["strengths"] = strengths

    never = []
    for b in _bullets(sections.get("never", [])):
        r = _parse_never(b)
        if r:
            never.append({"re": r[0], "label": r[1]})
    f["never"] = never
    f["approved"] = _bullets(sections.get("approved", []))
    f["rules"] = _kv(sections.get("rules", []))

    # Text that counts as "facts" for numbers and names.
    def section_text(key):
        if key == "me":
            keep = [ln for ln in sections.get("me", [])
                    if not any(fold(ln).lstrip("-* ").startswith(k) for k in CONTACT_KEYS)]
            return "\n".join(keep)
        return "\n".join(sections.get(key, []))

    f["number_text"] = "\n".join(section_text(k) for k in FACT_NUMBER_SECTIONS)
    # Strength AREA names are user-confirmed facts; their JD keywords are not.
    f["name_text"] = "\n".join([section_text(k) for k in FACT_NAME_SECTIONS] + [f["name"]]
                               + [s["area"] for s in strengths])
    f["salary_text"] = "\n".join(sal_lines)
    f["all_text"] = text or ""
    _lint(f)
    return f


def parse_languages(text: str) -> dict:
    """'English (C1), Hindi (native)' -> {'english': 'C1', 'hindi': 'native'}."""
    out = {}
    for part in _split_skills(text or ""):
        m = re.match(r"^([A-Za-zÀ-ž ]+?)\s*(?:\((.*?)\)|[-:–]\s*(.+))?$", part.strip())
        if m:
            out[fold(m.group(1))] = norm_space(m.group(2) or m.group(3) or "")
    return out


def _lint(f: dict) -> None:
    L = f["lint"]
    for key, label in (("name", "Name"), ("email", "Email")):
        if not f.get(key):
            L.append(("error", f"'## Me' is missing '- {label}: ...'"))
    if not f["home_country"]:
        L.append(("error", "'## Me' is missing '- Home country: <code>' (e.g. IN)"))
    if f["years"] is None:
        L.append(("warn", "'## Me' has no '- Total experience (years): N'"))
    if not f["jobs"]:
        L.append(("error", "'## Work history' has no jobs (format: '### Title | Company | City, Country | MM/YYYY – MM/YYYY')"))
    for j in f["jobs"]:
        if not j["company"] or not j["dates"]:
            L.append(("error", f"job heading '{j['title']}' needs 'Title | Company | Location | Dates'"))
        if not j["bullets"]:
            L.append(("error", f"job '{j['title']} | {j['company']}' has no bullet lines"))
    if not f["skills"]:
        L.append(("error", "'## Skills' is empty"))
    if not f["target_roles"]:
        L.append(("warn", "'## Targets' has no '- Roles: ...'"))
    if not f["target_countries"]:
        L.append(("warn", "'## Targets' has no '- Countries: ...'"))
    for code in f["target_countries"]:
        if code not in f["salary"]:
            L.append(("warn", f"no salary row for target country {code}"))
        if code != f["home_country"] and code not in f["visa"]:
            L.append(("warn", f"no visa line for target country {code}"))
    for code, row in f["salary"].items():
        if code not in COUNTRIES:
            L.append(("warn", f"salary row '{code}' is not a known country code"))
        if row["expected"] is None:
            L.append(("error", f"salary row {code}: expected amount missing"))
        if not row["period"]:
            L.append(("error", f"salary row {code}: unit '{row['unit']}' not understood (use e.g. LPA, EUR/year, AED/month)"))
    if not f["headline_titles"]:
        L.append(("warn", "'## Headline titles' is empty (CV headline will use your latest job title)"))
    if not f["strengths"]:
        L.append(("warn", "'## Strengths for fit scoring' is empty (fit score will be rough)"))


def load_facts(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return parse_facts(fh.read())


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: str | None) -> str:
    if not path:
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def find_job(facts: dict, company: str):
    k = company_key(company)
    for j in facts["jobs"]:
        if company_key(j["company"]) == k:
            return j
    for j in facts["jobs"]:
        jk = company_key(j["company"])
        if k and jk and (k in jk or jk in k):
            return j
    return None


def needs_visa(facts: dict, code: str) -> bool:
    code = country_code(code)
    if code == facts.get("home_country"):
        return False
    v = facts["visa"].get(code)
    if v is None:
        return True
    return bool(v["needs"])


# ---------------------------------------------------------------- salaries

CUR_PATTERNS = [
    ("EUR", r"€|\beur\b|euros?"),
    ("GBP", r"£|\bgbp\b"),
    ("INR", r"₹|\binr\b|\brs\.?|\blpa\b|lakhs?|\blacs?\b|crores?"),
    ("AED", r"\baed\b|\bdhs?\b|dirhams?"),
    ("SGD", r"\bs\$|\bsgd\b"),
    ("PLN", r"\bpln\b|zł"),
    ("USD", r"\busd\b|us\$|(?<![a-z])\$"),
]
_AMT = r"(\d[\d.,]*\s?(?:LPA|lpa|lakhs?|lacs?|L|k|K|m|M)?)"
RANGE_RE = re.compile(_AMT + r"\s*(?:-|–|—|to|bis|a|à)\s*(?:[^\d\n]{0,8})?" + _AMT)


def _amount(raw: str) -> float | None:
    s = raw.strip().lower().replace(" ", "")
    mult = 1.0
    for suf, m in (("lpa", 1e5), ("lakhs", 1e5), ("lakh", 1e5), ("lacs", 1e5), ("lac", 1e5), ("l", 1e5), ("k", 1e3), ("m", 1e6)):
        if s.endswith(suf):
            mult, s = m, s[: -len(suf)]
            break
    v = _to_float(s)
    return None if v is None else v * mult


def parse_salary(text: str) -> dict | None:
    """Find the first salary range in text.

    Returns {currency, min, max, period, text} with amounts in currency units
    (INR as rupees per year), or None. period: 'year' | 'month' | 'hour'.
    """
    if not text:
        return None
    for m in RANGE_RE.finditer(text):
        ctx = text[max(0, m.start() - 25): m.end() + 45]
        low = ctx.lower()
        cur = None
        for code, pat in CUR_PATTERNS:
            if re.search(pat, low):
                cur = code
                break
        if not cur:
            continue
        a, b = _amount(m.group(1)), _amount(m.group(2))
        if not a or not b:
            continue
        unit_b = re.search(r"(k|m|l|lakhs?|lacs?|lpa)$", m.group(2).strip().lower())
        unit_a = re.search(r"(k|m|l|lakhs?|lacs?|lpa)$", m.group(1).strip().lower())
        if unit_b and not unit_a:  # "70-80k" -> both thousands
            a = _amount(m.group(1).strip() + unit_b.group(1))
        if cur == "INR" and re.search(r"lpa|lakhs?|lacs?|\bl\b", low) and b < 1000:
            a, b = a * 1e5 if a < 1000 else a, b * 1e5
        if cur == "INR" and re.search(r"crores?|\bcr\b", low) and b < 100:
            a, b = a * 1e7, b * 1e7
        if b < a:
            continue
        after = text[m.end(): m.end() + 45].lower()
        if re.search(r"month|monthly|mth|p\.?\s?m\b|/\s?m\b|per mo|monat|mois|maand|miesi", after + low[-60:]):
            period = "month"
        elif re.search(r"hour|/\s?h\b|hourly", after):
            period = "hour"
        elif re.search(r"year|annum|annual|p\.?\s?a\b|yearly|lpa|ctc", after + low):
            period = "year"
        else:
            period = "month" if (cur in ("AED", "SGD", "PLN") and b < 100000) or (cur in ("EUR", "GBP", "USD") and b < 15000) else "year"
        if cur in ("EUR", "GBP", "USD") and b < 1000 and period == "year":
            a, b = a * 1000, b * 1000
        if b < 100:
            continue
        pre = re.search(r"(€|£|₹|S\$|US\$|\$|AED|SGD|EUR|GBP|INR|PLN|USD|Rs\.?)\s?$",
                        text[max(0, m.start() - 5): m.start()])
        shown = ((pre.group(1) + " ") if pre and len(pre.group(1)) > 2 else (pre.group(1) if pre else "")) + m.group(0)
        return {"currency": cur, "min": a, "max": b, "period": period, "text": norm_space(shown)}
    return None


def convert(amount: float, currency: str, period: str, to_currency: str, to_period: str) -> float | None:
    """Same currency only. Periods: year, month, hour, lpa (INR lakh per year)."""
    if amount is None or currency != to_currency:
        return None
    yearly = amount
    if period == "month":
        yearly = amount * 12
    elif period == "hour":
        yearly = amount * 2080
    elif period == "lpa":
        yearly = amount * 1e5
    if to_period == "month":
        return yearly / 12
    if to_period == "lpa":
        return yearly / 1e5
    if to_period == "hour":
        return yearly / 2080
    return yearly


def _step(currency: str, period: str) -> float:
    if period == "lpa":
        return 1
    if period == "month":
        return 500 if currency == "PLN" else 100
    return 1000


def format_money(value: float, currency: str, period: str, country: str = "") -> str:
    if period == "lpa":
        v = round(value, 1)
        return f"{v:g} LPA"
    n = f"{int(round(value)):,}"
    sym = {"EUR": "€", "GBP": "£", "USD": "US$", "SGD": "S$"}.get(currency)
    per = {"year": "/year", "month": "/month", "hour": "/hour"}.get(period, "")
    if currency == "PLN":
        return f"PLN {n} gross{per}"
    money = f"{sym}{n}" if sym else f"{currency} {n}"
    tail = ", excluding holiday pay" if country == "NL" and period == "year" else ""
    return f"{money}{per}{tail}"


def salary_answer(row: dict, posted: dict | None = None, override: str | None = None) -> dict:
    """Kairo salary rule.

    1. A number the user gave for this one job wins.
    2. Posted range in the same currency -> answer inside it, 40% up from the bottom
       (lower half), rounded; never below the user's minimum.
    3. No usable range -> the user's expected amount.
    """
    country = row.get("country", "")
    cur, per = row.get("currency", ""), row.get("period", "")
    out = {"basis": "", "value": None, "text": "", "flags": [], "range": None}
    if override:
        out.update(basis="override", text=override.strip())
        return out
    expected, minimum = row.get("expected"), row.get("minimum")
    lo = hi = None
    if posted:
        lo = convert(posted["min"], posted["currency"], posted["period"], cur, per)
        hi = convert(posted["max"], posted["currency"], posted["period"], cur, per)
        if lo is None:
            out["flags"].append(f"posted salary is in {posted['currency']}, your table uses {cur}: used your expected amount")
    if lo is not None and hi is not None and hi >= lo > 0:
        step = _step(cur, per)
        v = round((lo + 0.4 * (hi - lo)) / step) * step
        out["range"] = (lo, hi)
        out["basis"] = "range"
        if minimum and v < minimum:
            v = minimum
            out["basis"] = "range+minimum"
        if minimum and hi < minimum:
            out["flags"].append("posted range is below your minimum")
    else:
        v = expected
        out["basis"] = "expected"
    out["value"] = v
    if v is not None:
        out["text"] = format_money(v, cur, per, country)
    return out
