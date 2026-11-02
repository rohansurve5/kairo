"""JD scan signals on the 3 sample JDs and on tricky wording."""
import unittest
from datetime import date

from helpers import FACTS, fixture

from jd_scan import language_check, parse_experience, scan, sponsorship
from kairo_lib import load_facts, read_text

TODAY = date(2026, 11, 2)


def codes(r, severity=None):
    return {f["code"] for f in r["red_flags"] if severity is None or f["severity"] == severity}


class SampleJDs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = load_facts(FACTS)

    def test_india_good_fit(self):
        r = scan(self.facts, read_text(fixture("jd-in-bengaluru.txt")), "IN", "Product Manager – Merchant Payments",
                 "Nirvana Ledger", "Bengaluru", source="linkedin", today=TODAY)
        self.assertGreaterEqual(r["baseline"]["score"], 65)
        self.assertEqual(codes(r, "skip") | codes(r, "maybe"), set())
        self.assertEqual(r["verdict_hint"], "apply")
        self.assertFalse(r["needs_visa"])
        s = r["signals"]["salary"]
        self.assertEqual((s["currency"], s["min"], s["max"]), ("INR", 3000000, 4200000))
        self.assertEqual((r["signals"]["years"]["min"], r["signals"]["years"]["max"]), (5, 8))
        self.assertEqual(r["job"]["posted_at"], "2026-10-29")
        self.assertTrue(r["requirements"][0].startswith("5–8 years"))

    def test_netherlands_sponsor_and_optional_dutch(self):
        r = scan(self.facts, read_text(fixture("jd-nl-amsterdam.txt")), "NL", "Product Manager, Merchant Checkout",
                 "Tulip Commerce B.V.", "Amsterdam", posted="2026-10-25", source="company_site", today=TODAY)
        self.assertEqual(r["signals"]["sponsorship"]["value"], "yes")
        self.assertEqual(r["signals"]["languages_required"], [])
        self.assertEqual(codes(r, "skip") | codes(r, "maybe"), set())
        self.assertEqual(r["verdict_hint"], "apply")
        self.assertGreaterEqual(r["baseline"]["score"], 60)
        self.assertEqual(r["signals"]["salary"]["min"], 68000)

    def test_uae_blocks(self):
        r = scan(self.facts, read_text(fixture("jd-ae-dubai.txt")), "AE", "Senior Product Manager – Loyalty & CRM",
                 "Falcon Retail Group", "Dubai", today=TODAY)
        self.assertTrue({"years_above", "language_required", "local_only"} <= codes(r, "skip"))
        self.assertEqual(r["verdict_hint"], "skip")
        self.assertLess(r["baseline"]["score"], 60)

    def test_public_text_has_no_user_numbers(self):
        r = scan(self.facts, read_text(fixture("jd-ae-dubai.txt")), "AE", "Senior Product Manager", today=TODAY)
        for f in r["red_flags"]:
            self.assertNotRegex(f["public_text"], r"\d")

    def test_salary_below_floor_and_stale_posting(self):
        jd = "Product Manager, payments. Salary: €50,000 – €58,000 per year. 5+ years of product experience."
        r = scan(self.facts, jd, "NL", "Product Manager", posted="2026-10-10", source="linkedin", today=TODAY)
        self.assertIn("salary_below_floor", codes(r, "maybe"))  # Maybe: ask if the budget can reach the floor
        self.assertIn("stale_posting", codes(r))


    def test_visa_silent_abroad_is_maybe(self):
        jd = ("Product Manager, payments and checkout for SMB merchants. 5+ years of product experience. "
              "Hybrid in Amsterdam. " * 3)
        r = scan(self.facts, jd, "NL", "Product Manager", today=TODAY)
        self.assertIn("visa_unknown", codes(r, "maybe"))
        self.assertEqual(r["verdict_hint"], "maybe")


class Wording(unittest.TestCase):
    def test_sponsorship_negations(self):
        self.assertEqual(sponsorship("Visa sponsorship is not available for this role.")["value"], "no")
        self.assertEqual(sponsorship("We cannot sponsor work visas.")["value"], "no")
        self.assertEqual(sponsorship("We offer visa sponsorship and relocation support.")["value"], "yes")
        self.assertEqual(sponsorship("You must already have the right to work in the EU.")["value"], "no")
        self.assertEqual(sponsorship("We can't sponsor visas for remote roles. This role is in our Berlin office.")["value"], "unknown")
        self.assertEqual(sponsorship("A great team and free lunch.")["value"], "unknown")

    def test_experience_parsing(self):
        self.assertIsNone(parse_experience("We have been in business for over 25 years."))
        self.assertEqual(parse_experience("Minimum 7 years of experience in product.")["min"], 7)
        self.assertEqual(parse_experience("3-5 years experience as a PM")["max"], 5)

    def test_languages(self):
        self.assertEqual(language_check("German is a plus.", {}), [])
        self.assertEqual(language_check("Fluent German is required.", {})[0]["lang"], "German")
        self.assertEqual(language_check("Fluent German is required.", {"german": "C1"}), [])
        self.assertEqual(language_check("Our office is in Germany and the team is German.", {}), [])


if __name__ == "__main__":
    unittest.main()
