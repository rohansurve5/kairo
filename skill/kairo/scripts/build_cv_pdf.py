#!/usr/bin/env python3
"""Kairo CV / cover letter builder: cv.json -> ATS-friendly PDF (one column, real text, A4).

Uses reportlab (pre-installed in the Claude code sandbox per Anthropic's docs). If reportlab is
missing it writes a .docx (python-docx), and if that is missing too, a print-ready .html.
With --facts it runs the truth check first and refuses to build if the check fails.

Usage
  python3 build_cv_pdf.py cv.json --facts my-facts.md [--jd jd.txt] [--out Name_CV_Company.pdf]
  python3 build_cv_pdf.py --letter letter.json --facts my-facts.md --jd jd.txt [--out ...]
  options: --format auto|pdf|docx|html   --no-check (tests only)
Exit codes: 0 built, 1 truth check failed (nothing built), 2 bad input, 3 built but too many pages.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kairo_lib import country_code, load_json, word_count  # noqa: E402

FONT_DIR = os.path.join(os.path.dirname(HERE), "assets", "fonts")
OUT_DIR_CLAUDE = "/mnt/user-data/outputs"

# Country header rules. Keep in sync with references/country-formats.md.
COUNTRY_RULES = {
    "IN": {"nationality": False, "work_line": None, "gdpr": False, "signature": False, "max_pages": 2},
    "NL": {"nationality": True, "work_line": None, "gdpr": False, "signature": False, "max_pages": 2},
    "IE": {"nationality": True, "work_line": None, "gdpr": False, "signature": False, "max_pages": 2},
    "DE": {"nationality": True, "work_line": None, "gdpr": False, "signature": True, "max_pages": 2},
    "PL": {"nationality": True, "work_line": None, "gdpr": True, "signature": False, "max_pages": 2},
    "FR": {"nationality": True, "work_line": None, "gdpr": False, "signature": False, "max_pages": 2},
    "AE": {"nationality": True, "work_line": "Visa: needs an employment visa", "gdpr": False, "signature": False, "max_pages": 2},
    "SG": {"nationality": True, "work_line": "Requires Employment Pass", "gdpr": False, "signature": False, "max_pages": 2},
    "GB": {"nationality": False, "work_line": "Right to work: needs Skilled Worker visa sponsorship", "gdpr": False,
           "signature": False, "max_pages": 2},
}
DEFAULT_RULE = {"nationality": True, "work_line": None, "gdpr": False, "signature": False, "max_pages": 2}
PHOTO_OK = {"DE", "FR", "AE"}
DOB_OK = {"DE", "AE"}
GDPR_CLAUSE = ("I hereby consent to the processing of my personal data by {company} for the purposes of the current "
               "recruitment process, in accordance with Regulation (EU) 2016/679 (GDPR).")


def have(module):
    if module in os.environ.get("KAIRO_DISABLE", "").split(","):
        return False
    try:
        __import__(module)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------- content model (shared by all formats)

def rule_for(code):
    return COUNTRY_RULES.get(code, DEFAULT_RULE)


def header_lines(doc, kind="cv"):
    code = country_code(doc.get("country"))
    rule = rule_for(code)
    c = doc.get("contact", {}) or {}
    p = doc.get("personal", {}) or {}
    o = doc.get("options", {}) or {}
    home = country_code(p.get("home_country"))
    abroad = bool(home) and bool(code) and code != home
    loc = [c.get("location", "")]
    if abroad:
        if kind == "cv" and rule["nationality"] and p.get("nationality"):
            loc.append(f"Nationality: {p['nationality']}")
        if p.get("open_to_relocation"):
            loc.append("Open to relocation")
        if kind == "cv" and p.get("needs_visa") and rule["work_line"]:
            loc.append(rule["work_line"])
    if kind == "cv" and (o.get("include_dob") and p.get("date_of_birth")) and code in DOB_OK:
        loc.append(f"Date of birth: {p['date_of_birth']}")
    links = []
    if c.get("phone"):
        links.append(("tel:" + re.sub(r"[^\d+]", "", c["phone"]), c["phone"]))
    if c.get("email"):
        links.append(("mailto:" + c["email"], c["email"]))
    for key in ("linkedin", "website"):
        v = c.get(key)
        if v:
            url = v if re.match(r"^https?://", v) else "https://" + v
            links.append((url, re.sub(r"^https?://(www\.)?", "", v).rstrip("/")))
    return [x for x in loc if x], links


def cv_sections(cv):
    """Ordered list of (title, kind, items)."""
    code = country_code(cv.get("country"))
    secs = []
    if cv.get("summary"):
        secs.append(("Professional Summary", "para", [cv["summary"]]))
    exp = ("Work Experience", "jobs", cv.get("experience", []))
    proj = ("Projects", "projects", cv.get("projects", []))
    order = [proj, exp] if (cv.get("options") or {}).get("projects_first") else [exp, proj]
    secs += [s for s in order if s[2]]
    if cv.get("skills"):
        secs.append(("Skills", "para", [", ".join(cv["skills"])]))
    if cv.get("education"):
        secs.append(("Education", "lines", cv["education"]))
    if cv.get("certifications"):
        secs.append(("Certifications", "bullets", cv["certifications"]))
    if cv.get("languages"):
        title = "Languages (CEFR)" if code == "DE" else "Languages"
        secs.append((title, "para", [" · ".join(cv["languages"])]))
    if cv.get("additional"):
        secs.append(("Additional Information", "bullets", cv["additional"]))
    return secs


def footer_lines(cv):
    code = country_code(cv.get("country"))
    rule = rule_for(code)
    out = []
    if rule["gdpr"]:
        company = (cv.get("target") or {}).get("company") or "the employer"
        out.append(GDPR_CLAUSE.format(company=company))
    if rule["signature"]:
        city = (cv.get("contact", {}).get("location", "") or "").split(",")[0].strip()
        out.append(f"{city}, {date.today().strftime('%d.%m.%Y')} – {cv.get('name', '')}")
    return out


def plain_text(doc, kind):
    """Every word the reader should see; used to check nothing was cut off in the PDF."""
    loc, links = header_lines(doc, kind)
    parts = [doc.get("name", ""), doc.get("headline", ""), " | ".join(loc), " | ".join(t for _, t in links)]
    if kind == "cv":
        for title, k, items in cv_sections(doc):
            parts.append(title)
            for it in items:
                if k == "jobs":
                    parts += [it.get("title", ""), it.get("company", ""), it.get("location", ""), it.get("dates", "")]
                    parts += it.get("bullets", [])
                elif k == "projects":
                    parts += [it.get("name", ""), it.get("dates", "")] + it.get("bullets", []) + [it.get("text", "")]
                else:
                    parts.append(it)
        parts += footer_lines(doc)
    else:
        parts += [doc.get("date", ""), f"Re: {doc.get('role', '')} – {doc.get('company', '')}", doc.get("greeting", "")]
        parts += doc.get("paragraphs", []) + [doc.get("closing", ""), doc.get("name", "")]
    return "\n".join(x for x in parts if x)


def default_name(doc, kind):
    def slug(s):
        s = re.sub(r"[^\w\s-]", "", s or "", flags=re.U)
        return re.sub(r"[\s-]+", "_", s.strip())[:40]
    t = doc.get("target") or {}
    company = t.get("company") or doc.get("company", "")
    role = t.get("role") or doc.get("role", "")
    bits = [slug(doc.get("name", "CV")), "CV" if kind == "cv" else "Cover_Letter", slug(company), slug(role)]
    return "_".join(b for b in bits if b)


def resolve_out(out, doc, kind, ext):
    base_dir = OUT_DIR_CLAUDE if os.path.isdir(OUT_DIR_CLAUDE) else os.getcwd()
    if not out:
        return os.path.join(base_dir, default_name(doc, kind) + "." + ext)
    root, cur_ext = os.path.splitext(out)
    if not os.path.dirname(out):
        root = os.path.join(base_dir, root)
    return root + "." + ext if cur_ext.lower() != "." + ext else root + cur_ext


# ---------------------------------------------------------------- PDF (reportlab)

def _fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    reg, bold = os.path.join(FONT_DIR, "Geist-Regular.ttf"), os.path.join(FONT_DIR, "Geist-Bold.ttf")
    if os.path.exists(reg) and os.path.exists(bold):
        try:
            pdfmetrics.registerFont(TTFont("KairoSans", reg))
            pdfmetrics.registerFont(TTFont("KairoSans-Bold", bold))
            from reportlab.lib.fonts import addMapping
            addMapping("KairoSans", 0, 0, "KairoSans")
            addMapping("KairoSans", 1, 0, "KairoSans-Bold")
            addMapping("KairoSans", 0, 1, "KairoSans")
            addMapping("KairoSans", 1, 1, "KairoSans-Bold")
            cmap = TTFont("KairoProbe", reg).face.charToGlyph
            return "KairoSans", "KairoSans-Bold", (lambda ch: ord(ch) in cmap), "Geist"
        except Exception:  # noqa: BLE001 - any font problem -> built-in font
            pass

    def winansi(ch):
        try:
            ch.encode("cp1252")
            return True
        except UnicodeEncodeError:
            return False
    return "Helvetica", "Helvetica-Bold", winansi, "Helvetica"


REPLACE = {"₹": "INR ", "→": "->", "←": "<-", "✓": "-", "−": "-", "‑": "-", " ": " "}


def _safe(text, ok):
    out = []
    for ch in text or "":
        if ch in "\n\t" or ok(ch):
            out.append(ch)
        else:
            out.append(REPLACE.get(ch, "?"))
    return "".join(out)


def build_pdf(doc, kind, path):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    regular, bold, ok, font_name = _fonts()
    ink, grey, rule_c = colors.HexColor("#111111"), colors.HexColor("#444444"), colors.HexColor("#BBBBBB")
    body_size = 9.4 if kind == "cv" else 10.4
    st = {
        "name": ParagraphStyle("name", fontName=bold, fontSize=17, leading=20, textColor=ink, spaceAfter=1),
        "headline": ParagraphStyle("headline", fontName=regular, fontSize=10.5, leading=13.5, textColor=grey),
        "meta": ParagraphStyle("meta", fontName=regular, fontSize=8.8, leading=11.5, textColor=grey),
        "h": ParagraphStyle("h", fontName=bold, fontSize=9.8, leading=12, textColor=ink, spaceBefore=7, spaceAfter=1.5,
                            keepWithNext=1),
        "body": ParagraphStyle("body", fontName=regular, fontSize=body_size, leading=body_size * 1.32, textColor=ink,
                               alignment=TA_LEFT, spaceAfter=2 if kind == "cv" else 7),
        "role": ParagraphStyle("role", fontName=regular, fontSize=body_size, leading=body_size * 1.32, textColor=ink,
                               spaceBefore=3.5, spaceAfter=1, keepWithNext=1),
        "bullet": ParagraphStyle("bullet", fontName=regular, fontSize=body_size, leading=body_size * 1.3, textColor=ink,
                                 leftIndent=10, bulletIndent=1.5, spaceAfter=1),
        "small": ParagraphStyle("small", fontName=regular, fontSize=7.8, leading=10, textColor=grey, spaceBefore=8),
    }

    def esc(t):
        return html.escape(_safe(t, ok), quote=False)

    def link(url, text):
        return f'<a href="{html.escape(url)}" color="#111111">{esc(text)}</a>'

    # Optional photo (decision 5: only DE / FR / AE, off by default, only when the user asked).
    photo = None
    p_opts, p_pers = doc.get("options") or {}, doc.get("personal") or {}
    if kind == "cv" and p_opts.get("include_photo") and p_pers.get("photo"):
        if country_code(doc.get("country")) in PHOTO_OK and os.path.exists(p_pers["photo"]):
            photo = p_pers["photo"]
        else:
            print("Kairo build: photo skipped (country does not use photos, or file not found)")
    head_indent = 34 * mm if photo else 0
    for key in ("name", "headline", "meta"):
        st[key].rightIndent = head_indent

    story = []
    name = doc.get("name", "")
    story.append(Paragraph(esc(name), st["name"]))
    if doc.get("headline"):
        story.append(Paragraph(esc(doc["headline"]), st["headline"]))
    loc, links = header_lines(doc, kind)
    if loc:
        story.append(Paragraph(esc(" | ".join(loc)), st["meta"]))
    if links:
        story.append(Paragraph(" | ".join(link(u, t) for u, t in links), st["meta"]))
    if photo:
        story.append(Spacer(1, 8 * mm))

    def heading(title):
        # keepWithNext (never nested KeepTogether: reportlab reports a huge height for those and breaks the page)
        hr = HRFlowable(width="100%", thickness=0.5, color=rule_c, spaceBefore=0, spaceAfter=2.5)
        hr.keepWithNext = 1
        return [Paragraph(esc(title), st["h"]), hr]

    if kind == "cv":
        for title, k, items in cv_sections(doc):
            blocks = []
            if k in ("para", "lines"):
                blocks = [Paragraph(esc(t), st["body"]) for t in items]
            elif k == "bullets":
                blocks = [Paragraph(esc(t), st["bullet"], bulletText="•") for t in items]
            elif k == "jobs":
                for e in items:
                    meta = ", ".join(x for x in (e.get("company", ""), e.get("location", "")) if x)
                    role = f"<b>{esc(e.get('title', ''))}</b> – {esc(meta)} | {esc(e.get('dates', ''))}"
                    blocks.append(Paragraph(role, st["role"]))
                    blocks += [Paragraph(esc(b), st["bullet"], bulletText="•") for b in e.get("bullets", [])]
            elif k == "projects":
                for p in items:
                    nm = link(p["url"], p.get("name", "")) if p.get("url") else esc(p.get("name", ""))
                    line = f"<b>{nm}</b>" + (f" | {esc(p['dates'])}" if p.get("dates") else "")
                    if p.get("text"):
                        line += f" – {esc(p['text'])}"
                    blocks.append(Paragraph(line, st["role"]))
                    blocks += [Paragraph(esc(b), st["bullet"], bulletText="•") for b in p.get("bullets", [])]
            if blocks:
                story += heading(title) + blocks
        for line in footer_lines(doc):
            story.append(Paragraph(esc(line), st["small"]))
    else:
        story.append(Spacer(1, 10))
        for line in (doc.get("date", ""), f"Re: {doc.get('role', '')} – {doc.get('company', '')}"):
            if line.strip(" –:Re"):
                story.append(Paragraph(esc(line), st["body"]))
        if doc.get("greeting"):
            story.append(Paragraph(esc(doc["greeting"]), st["body"]))
        for ptxt in doc.get("paragraphs", []):
            story.append(Paragraph(esc(ptxt), st["body"]))
        story.append(Paragraph(esc(doc.get("closing", "Kind regards,")) + "<br/>" + esc(name), st["body"]))

    title = os.path.splitext(os.path.basename(path))[0]
    t = doc.get("target") or {}
    subject = ("CV" if kind == "cv" else "Cover letter") + (
        f" – {t.get('role') or doc.get('role', '')} – {t.get('company') or doc.get('company', '')}")
    pdf = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm,
                            bottomMargin=13 * mm, title=title, author=name, subject=subject,
                            creator="Kairo (open source job-search skill)", lang="en")
    def first_page(canvas, _doc):
        if photo:
            w, h = 28 * mm, 36 * mm
            canvas.drawImage(photo, A4[0] - 15 * mm - w, A4[1] - 13 * mm - h, width=w, height=h,
                             preserveAspectRatio=True, anchor="ne", mask="auto")

    pdf.build(story, onFirstPage=first_page)
    return {"font": font_name, "pages_reportlab": pdf.page, "photo": bool(photo)}


# ---------------------------------------------------------------- DOCX fallback (python-docx)

def _docx_link(paragraph, url, text):
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    h.append(run)
    paragraph._p.append(h)


def build_docx(doc, kind, path):
    import docx
    from docx.shared import Mm, Pt
    d = docx.Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(16)
    sec.top_margin = sec.bottom_margin = Mm(14)
    normal = d.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9.5 if kind == "cv" else 10.5)

    def para(text="", bold=False, size=None, style=None):
        p = d.add_paragraph(style=style)
        if text:
            r = p.add_run(text)
            r.bold = bold
            if size:
                r.font.size = Pt(size)
        p.paragraph_format.space_after = Pt(2)
        return p

    para(doc.get("name", ""), bold=True, size=16)
    if doc.get("headline"):
        para(doc["headline"], size=10.5)
    loc, links = header_lines(doc, kind)
    if loc:
        para(" | ".join(loc), size=9)
    if links:
        p = para(size=9)
        for i, (u, t) in enumerate(links):
            if i:
                p.add_run(" | ")
            _docx_link(p, u, t)
    if kind == "cv":
        for title, k, items in cv_sections(doc):
            h = para(title.upper(), bold=True, size=10)
            h.paragraph_format.space_before = Pt(8)
            for it in items:
                if k == "jobs":
                    p = para()
                    p.add_run(it.get("title", "")).bold = True
                    meta = ", ".join(x for x in (it.get("company", ""), it.get("location", "")) if x)
                    p.add_run(f" – {meta} | {it.get('dates', '')}")
                    for b in it.get("bullets", []):
                        para(b, style="List Bullet")
                elif k == "projects":
                    p = para()
                    p.add_run(it.get("name", "")).bold = True
                    if it.get("dates"):
                        p.add_run(f" | {it['dates']}")
                    if it.get("text"):
                        p.add_run(f" – {it['text']}")
                    for b in it.get("bullets", []):
                        para(b, style="List Bullet")
                elif k == "bullets":
                    para(it, style="List Bullet")
                else:
                    para(it)
        for line in footer_lines(doc):
            para(line, size=8)
    else:
        para()
        para(doc.get("date", ""))
        para(f"Re: {doc.get('role', '')} – {doc.get('company', '')}")
        para(doc.get("greeting", ""))
        for ptxt in doc.get("paragraphs", []):
            para(ptxt).paragraph_format.space_after = Pt(8)
        para(doc.get("closing", "Kind regards,"))
        para(doc.get("name", ""))
    d.core_properties.title = os.path.splitext(os.path.basename(path))[0]
    d.core_properties.author = doc.get("name", "")
    d.save(path)
    return {"font": "Arial"}


# ---------------------------------------------------------------- HTML fallback (standard library)

def build_html(doc, kind, path):
    e = lambda s: html.escape(s or "")  # noqa: E731
    loc, links = header_lines(doc, kind)
    out = [f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>{e(os.path.splitext(os.path.basename(path))[0])}</title>",
           "<style>@page{size:A4;margin:14mm 16mm}body{font:9.5pt/1.35 Arial,Helvetica,sans-serif;color:#111;max-width:178mm;margin:auto}"
           "h1{font-size:17pt;margin:0}h2{font-size:10pt;text-transform:uppercase;border-bottom:.5pt solid #bbb;margin:9pt 0 3pt}"
           ".m{color:#444;font-size:8.8pt;margin:1pt 0}p{margin:2pt 0}ul{margin:1pt 0 3pt 14pt;padding:0}a{color:#111}"
           ".s{font-size:7.8pt;color:#444;margin-top:8pt}</style></head><body>",
           f"<!-- Kairo: open this file and use Print > Save as PDF (A4) -->", f"<h1>{e(doc.get('name'))}</h1>"]
    if doc.get("headline"):
        out.append(f"<p class=\"m\">{e(doc['headline'])}</p>")
    if loc:
        out.append(f"<p class=\"m\">{e(' | '.join(loc))}</p>")
    if links:
        out.append("<p class=\"m\">" + " | ".join(f"<a href=\"{e(u)}\">{e(t)}</a>" for u, t in links) + "</p>")
    if kind == "cv":
        for title, k, items in cv_sections(doc):
            out.append(f"<h2>{e(title)}</h2>")
            for it in items:
                if k == "jobs":
                    meta = ", ".join(x for x in (it.get("company", ""), it.get("location", "")) if x)
                    out.append(f"<p><b>{e(it.get('title'))}</b> – {e(meta)} | {e(it.get('dates'))}</p><ul>"
                               + "".join(f"<li>{e(b)}</li>" for b in it.get("bullets", [])) + "</ul>")
                elif k == "projects":
                    nm = f"<a href=\"{e(it['url'])}\">{e(it.get('name'))}</a>" if it.get("url") else e(it.get("name"))
                    dates = " | " + e(it["dates"]) if it.get("dates") else ""
                    desc = " – " + e(it["text"]) if it.get("text") else ""
                    out.append(f"<p><b>{nm}</b>{dates}{desc}</p>")
                    if it.get("bullets"):
                        out.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in it["bullets"]) + "</ul>")
                elif k == "bullets":
                    out.append(f"<ul><li>{e(it)}</li></ul>")
                else:
                    out.append(f"<p>{e(it)}</p>")
        out += [f"<p class=\"s\">{e(x)}</p>" for x in footer_lines(doc)]
    else:
        out.append(f"<p>&nbsp;</p><p>{e(doc.get('date'))}</p><p>Re: {e(doc.get('role'))} – {e(doc.get('company'))}</p>")
        out.append(f"<p>{e(doc.get('greeting'))}</p>")
        out += [f"<p style=\"margin-bottom:7pt\">{e(x)}</p>" for x in doc.get("paragraphs", [])]
        out.append(f"<p>{e(doc.get('closing', 'Kind regards,'))}<br>{e(doc.get('name'))}</p>")
    out.append("</body></html>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    return {"font": "Arial (browser)"}


# ---------------------------------------------------------------- self-check of the PDF

def pdf_check(path, expected_text, max_pages):
    if not have("pypdf"):
        return {"checked": False, "note": "pypdf not available: page count from reportlab only"}
    from pypdf import PdfReader
    r = PdfReader(path)
    text = "\n".join((p.extract_text() or "") for p in r.pages)

    def toks(s):
        s = re.sub(r"[-‐-―]", "", (s or "").lower())
        return re.findall(r"[\w₹€$+%]+", s, re.U)
    bag = {}
    for t in toks(text):
        bag[t] = bag.get(t, 0) + 1
    missing = []
    for t in toks(expected_text):
        if bag.get(t):
            bag[t] -= 1
        else:
            missing.append(t)
    exp_n = max(1, len(toks(expected_text)))
    links = []
    for page in r.pages:
        for a in page.get("/Annots") or []:
            o = a.get_object()
            act = o.get("/A")
            if act and act.get("/URI"):
                links.append(str(act["/URI"]))
    meta = r.metadata or {}
    return {"checked": True, "pages": len(r.pages), "text_chars": len(text), "missing_words": missing[:20],
            "missing_pct": round(100 * len(missing) / exp_n, 1), "links": len(links),
            "title": str(meta.get("/Title", "")), "too_many_pages": len(r.pages) > max_pages}


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Kairo CV / cover letter builder")
    ap.add_argument("cv", nargs="?", help="cv.json")
    ap.add_argument("--letter", help="letter.json (build a cover letter instead of a CV)")
    ap.add_argument("--facts", help="my-facts.md (runs the truth check first; strongly recommended)")
    ap.add_argument("--jd", help="job description text (lets the cover letter use JD numbers and names)")
    ap.add_argument("--out", help="output file name (saved in /mnt/user-data/outputs when that folder exists)")
    ap.add_argument("--format", default="auto", choices=["auto", "pdf", "docx", "html"])
    ap.add_argument("--no-check", action="store_true", help="skip the truth check (tests only)")
    a = ap.parse_args(argv)
    if not a.cv and not a.letter:
        ap.error("give cv.json or --letter letter.json")
    kind = "letter" if a.letter else "cv"
    try:
        doc = load_json(a.letter or a.cv)
    except (OSError, ValueError) as exc:
        print(f"Kairo build: cannot read input: {exc}", file=sys.stderr)
        return 2

    if a.facts and not a.no_check:
        import truth_check
        rep, _ = truth_check.run(a.facts, cv=None if a.letter else a.cv, letter=a.letter, jd_path=a.jd)
        if rep.errors:
            truth_check.print_report(rep)
            print("Kairo build: NOT built because the truth check failed.")
            return 1
        print(f"Kairo build: truth check PASS ({len(rep.warnings)} warnings)")
    elif not a.no_check:
        print("Kairo build: WARNING truth check skipped (no --facts). Run truth_check.py before showing this file.")

    fmt = a.format
    if fmt == "auto":
        fmt = "pdf" if have("reportlab") else "docx" if have("docx") else "html"
    if fmt == "pdf" and not have("reportlab"):
        print("Kairo build: reportlab is not installed. Try: pip install reportlab   (or use --format docx/html)")
        return 2
    ext = {"pdf": "pdf", "docx": "docx", "html": "html"}[fmt]
    path = resolve_out(a.out, doc, kind, ext)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    info = {"pdf": build_pdf, "docx": build_docx, "html": build_html}[fmt](doc, kind, path)

    code = country_code(doc.get("country"))
    max_pages = int((doc.get("options") or {}).get("max_pages") or (rule_for(code)["max_pages"] if kind == "cv" else 1))
    result = {"file": path, "format": fmt, "font": info.get("font"), "words": word_count(plain_text(doc, kind)),
              "country": code}
    status = 0
    if fmt == "pdf":
        chk = pdf_check(path, plain_text(doc, kind), max_pages)
        result.update(chk)
        if not chk.get("checked"):
            result["pages"] = info.get("pages_reportlab")
            chk["too_many_pages"] = (result["pages"] or 0) > max_pages
        if chk.get("too_many_pages"):
            print(f"Kairo build: {result['pages']} pages (max {max_pages}): cut the least relevant bullets and build again.")
            status = 3
        if chk.get("checked") and chk["missing_pct"] > 1:
            print(f"Kairo build: WARNING {chk['missing_pct']}% of words not found in the PDF text: {chk['missing_words'][:8]}")
    else:
        note = "Open the .docx in Word or Google Docs and export as PDF." if fmt == "docx" else \
            "Open the .html file in a browser and use Print > Save as PDF (A4)."
        result["note"] = f"PDF library not available, so Kairo made a .{fmt} file instead. {note}"
        print("Kairo build: " + result["note"])
    print("KAIRO_RESULT " + json.dumps(result, ensure_ascii=False))
    return status


if __name__ == "__main__":
    sys.exit(main())
