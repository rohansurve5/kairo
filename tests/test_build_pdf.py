"""PDF builder: 1-2 pages, selectable text, correct country header, fallbacks, truth-check gate."""
import os
import re
import subprocess
import sys
import unittest
from datetime import date

from helpers import FACTS, OUTPUT, SCRIPTS, fixture, mutated, write_tmp

BUILD = os.path.join(SCRIPTS, "build_cv_pdf.py")
OUT = os.path.join(OUTPUT, "pdf-tests")
NEEDS_VISA = {"IN": False, "NL": True, "IE": True, "DE": True, "PL": True, "FR": True, "AE": True, "SG": True, "GB": True}


def build(args, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, BUILD] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def pdf_text(path):
    from pypdf import PdfReader
    return "\n".join(pg.extract_text() or "" for pg in PdfReader(path).pages)


def norm(s):
    return re.sub(r"\s+", " ", s)


class RealCVs(unittest.TestCase):
    def test_three_country_cvs(self):
        from pypdf import PdfReader
        expect = {
            "in": ("Pune, India", ["Nationality", "Open to relocation", "visa"]),
            "nl": ("Pune, India | Nationality: Indian | Open to relocation", ["Employment Pass", "Visa:"]),
            "ae": ("Pune, India | Nationality: Indian | Open to relocation | Visa: needs an employment visa", []),
        }
        for c, (header, absent) in expect.items():
            out = os.path.join(OUT, f"Priya_Sharma_CV_{c}.pdf")
            code, log = build([fixture(f"cv-{c}.json"), "--facts", FACTS, "--out", out])
            self.assertEqual(code, 0, log)
            r = PdfReader(out)
            self.assertIn(len(r.pages), (1, 2))
            text = norm(pdf_text(out))
            self.assertIn("Priya Sharma", text)
            self.assertIn(header, text)
            first_lines = text.split("Professional Summary")[0]
            for word in absent:
                self.assertNotIn(word, first_lines, f"{c}: header should not contain {word}")
            self.assertIn("Kestrel Payments", text)
            self.assertIn("₹4,50,000" if c != "ae" else "250,000", text)
            self.assertEqual(r.metadata.title, f"Priya_Sharma_CV_{c}")
            self.assertEqual(r.metadata.author, "Priya Sharma")
            fonts = {str(f) for pg in r.pages for f in (pg["/Resources"].get("/Font") or {}).values()}
            base = {str(pg["/Resources"]["/Font"][k].get_object()["/BaseFont"]) for pg in r.pages for k in pg["/Resources"]["/Font"]}
            self.assertTrue(any("Geist" in b for b in base), base)
            self.assertTrue(fonts)
            links = [a.get_object()["/A"]["/URI"] for pg in r.pages for a in (pg.get("/Annots") or [])]
            self.assertIn("mailto:priya.sharma@example.com", links)

    def test_cover_letter_one_page(self):
        out = os.path.join(OUT, "Priya_Sharma_Cover_Letter_nl.pdf")
        code, log = build(["--letter", fixture("letter-nl.json"), "--facts", FACTS, "--jd", fixture("jd-nl-amsterdam.txt"), "--out", out])
        self.assertEqual(code, 0, log)
        from pypdf import PdfReader
        self.assertEqual(len(PdfReader(out).pages), 1)
        self.assertIn("Dear Tulip Commerce hiring team", pdf_text(out))


class CountryHeaders(unittest.TestCase):
    def test_all_nine_countries(self):
        today = date.today().strftime("%d.%m.%Y")
        must = {
            "IN": ["Pune, India"],
            "NL": ["Nationality: Indian", "Open to relocation"],
            "IE": ["Nationality: Indian", "Open to relocation"],
            "DE": ["Nationality: Indian", "Languages (CEFR)", f"Pune, {today}"],
            "PL": ["Nationality: Indian", "processing of my personal data by Tulip Commerce B.V.", "2016/679"],
            "FR": ["Nationality: Indian"],
            "AE": ["Visa: needs an employment visa"],
            "SG": ["Requires Employment Pass"],
            "GB": ["Right to work: needs Skilled Worker visa sponsorship", "Open to relocation"],
        }
        never = {"IN": ["Nationality"], "GB": ["Nationality"], "NL": ["Employment Pass", "GDPR"], "SG": ["GDPR"]}
        for code_, words in must.items():
            def f(cv, c=code_):
                cv["country"] = c
                cv["personal"]["needs_visa"] = NEEDS_VISA[c]
            path = write_tmp(mutated("cv-nl.json", f), f"cv-{code_}.json")
            out = os.path.join(OUT, f"header_{code_}.pdf")
            rc, log = build([path, "--no-check", "--out", out])
            self.assertEqual(rc, 0, log)
            text = norm(pdf_text(out))
            for w in words:
                self.assertIn(w, text, f"{code_}: missing {w!r}")
            for w in never.get(code_, []):
                self.assertNotIn(w, text, f"{code_}: should not contain {w!r}")


class Gates(unittest.TestCase):
    def test_invented_number_is_not_built(self):
        out = os.path.join(OUT, "should_not_exist.pdf")
        if os.path.exists(out):
            os.remove(out)
        rc, log = build([fixture("cv-nl-invented-number.json"), "--facts", FACTS, "--out", out])
        self.assertEqual(rc, 1)
        self.assertIn("NOT built", log)
        self.assertFalse(os.path.exists(out))

    def test_too_many_pages_exit_3(self):
        def f(cv):
            cv["experience"][0]["bullets"] = cv["experience"][0]["bullets"] * 14
        out = os.path.join(OUT, "too_long.pdf")
        rc, log = build([write_tmp(mutated("cv-nl.json", f), "cv-long.json"), "--no-check", "--out", out])
        self.assertEqual(rc, 3, log)

    def test_photo_only_where_allowed(self):
        from PIL import Image
        img = os.path.join(OUT, "fake-photo.png")
        os.makedirs(OUT, exist_ok=True)
        Image.new("RGB", (300, 400), (200, 200, 210)).save(img)

        def f(cv, c):
            cv["country"] = c
            cv["options"]["include_photo"] = True
            cv["personal"]["photo"] = img
        rc, log = build([write_tmp(mutated("cv-nl.json", lambda cv: f(cv, "DE")), "cv-de-photo.json"), "--no-check",
                         "--out", os.path.join(OUT, "photo_de.pdf")])
        self.assertEqual(rc, 0, log)
        self.assertNotIn("photo skipped", log)
        rc, log = build([write_tmp(mutated("cv-nl.json", lambda cv: f(cv, "NL")), "cv-nl-photo.json"), "--no-check",
                         "--out", os.path.join(OUT, "photo_nl.pdf")])
        self.assertIn("photo skipped", log)


class Fallbacks(unittest.TestCase):
    def test_docx_when_reportlab_missing(self):
        out = os.path.join(OUT, "fallback.pdf")
        rc, log = build([fixture("cv-nl.json"), "--facts", FACTS, "--out", out], {"KAIRO_DISABLE": "reportlab"})
        self.assertEqual(rc, 0, log)
        path = os.path.join(OUT, "fallback.docx")
        self.assertTrue(os.path.exists(path))
        import docx
        text = "\n".join(p.text for p in docx.Document(path).paragraphs)
        self.assertIn("Kestrel Payments", text)
        self.assertIn("Nationality: Indian", text)

    def test_html_when_no_libraries(self):
        out = os.path.join(OUT, "fallback2.pdf")
        rc, log = build([fixture("cv-nl.json"), "--facts", FACTS, "--out", out], {"KAIRO_DISABLE": "reportlab,docx"})
        self.assertEqual(rc, 0, log)
        with open(os.path.join(OUT, "fallback2.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("Priya Sharma", html)
        self.assertIn("Save as PDF", html)


if __name__ == "__main__":
    unittest.main()
