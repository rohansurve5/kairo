"""Standard form answers and the salary rule."""
import unittest

from helpers import FACTS, fixture

from form_answers import build
from kairo_lib import load_facts, read_text, salary_answer


def rows(r):
    return dict(r["rows"])


class Salary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = load_facts(FACTS)

    def test_nl_range_lower_half(self):
        r = build(self.f, "NL", read_text(fixture("jd-nl-amsterdam.txt")), company="Tulip Commerce", city="Amsterdam")
        self.assertEqual(r["salary"]["text"], "€74,000/year, excluding holiday pay")  # 68k + 40% of 14k = 73.6k
        self.assertEqual(rows(r)["Will you need visa sponsorship?"], "Yes")
        self.assertTrue(rows(r)["Current location"].endswith("(open to relocation)"))
        self.assertIn("Nationality", rows(r))

    def test_india_ctc_style(self):
        r = build(self.f, "IN", read_text(fixture("jd-in-bengaluru.txt")), city="Bengaluru")
        rr = rows(r)
        self.assertEqual(rr["Expected CTC"], "35 LPA (negotiable)")  # 30 + 40% of 12 = 34.8 -> 35
        self.assertEqual(rr["Current CTC"], "28 LPA (24 fixed + 4 variable)")
        self.assertEqual(rr["Notice period (days)"], "60")
        self.assertNotIn("Nationality", rr)
        self.assertIn("open to relocating to Bengaluru", rr["Current location"])

    def test_uae_raised_to_minimum(self):
        r = build(self.f, "AE", read_text(fixture("jd-ae-dubai.txt")))
        self.assertEqual(r["salary"]["text"], "AED 28,000/month")  # 27,000 from the range, minimum 28,000
        self.assertEqual(r["salary"]["basis"], "range+minimum")

    def test_range_below_minimum_is_flagged(self):
        r = build(self.f, "NL", "Salary €50,000 – €58,000 per year")
        self.assertEqual(r["salary"]["value"], 62000)
        self.assertIn("posted range is below your minimum", r["flags"])

    def test_no_range_uses_expected_and_override_wins(self):
        r = build(self.f, "NL", "No salary in this JD.")
        self.assertEqual(r["salary"]["text"], "€72,000/year, excluding holiday pay")
        r = build(self.f, "NL", "", override="€80,000/year")
        self.assertEqual(r["salary"]["text"], "€80,000/year")

    def test_missing_salary_is_asked_never_guessed(self):
        r = build(self.f, "GB", "Salary: £60,000 – £70,000 per year")
        rr = rows(r)
        self.assertTrue(rr["Expected salary"].startswith("ASK THE USER"))
        self.assertIsNone(r["salary"])
        self.assertNotIn("Minimum salary (only if the form asks)", rr)
        r = build(self.f, "GB", "", override="£70,000/year")
        self.assertEqual(r["salary"]["text"], "£70,000/year")

    def test_other_currency_falls_back(self):
        row = self.f["salary"]["NL"]
        out = salary_answer(row, {"currency": "USD", "min": 90000, "max": 110000, "period": "year"})
        self.assertEqual(out["basis"], "expected")
        self.assertTrue(out["flags"])


if __name__ == "__main__":
    unittest.main()
