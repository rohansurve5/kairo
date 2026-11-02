"""Truth check: passes on good input, fails on invented or moved facts. Fake user only."""
import unittest

from helpers import FACTS, fixture, mutated, write_tmp

import truth_check
from kairo_lib import load_facts, number_values, parse_salary

JD_NL = fixture("jd-nl-amsterdam.txt")


def run_cv(obj, name="cv.json"):
    rep, _ = truth_check.run(FACTS, cv=write_tmp(obj, name))
    return rep


def msgs(rep):
    return " | ".join(i["msg"] for i in rep.errors)


class GoodInput(unittest.TestCase):
    def test_facts_lint_passes(self):
        rep, facts = truth_check.run(FACTS, lint=True)
        self.assertEqual(rep.errors, [])
        self.assertEqual(len(facts["jobs"]), 3)

    def test_three_cvs_pass(self):
        for c in ("in", "nl", "ae"):
            rep, _ = truth_check.run(FACTS, cv=fixture(f"cv-{c}.json"))
            self.assertEqual(rep.errors, [], f"cv-{c}: {msgs(rep)}")

    def test_letter_and_answers_pass_with_jd(self):
        rep, _ = truth_check.run(FACTS, letter=fixture("letter-nl.json"), answers=fixture("answers-nl.json"), jd_path=JD_NL)
        self.assertEqual(rep.errors, [], msgs(rep))
        self.assertLessEqual(rep.stats["letter"]["words"], 250)


class InventedFacts(unittest.TestCase):
    def test_invented_number_fixture_fails(self):
        rep, _ = truth_check.run(FACTS, cv=fixture("cv-nl-invented-number.json"))
        self.assertTrue(rep.errors)
        self.assertIn('number "98"', msgs(rep))

    def test_cli_exit_code_is_1_on_fail(self):
        self.assertEqual(truth_check.main(["--facts", FACTS, "--cv", fixture("cv-nl-invented-number.json")]), 1)
        self.assertEqual(truth_check.main(["--facts", FACTS, "--cv", fixture("cv-nl.json")]), 0)

    def test_number_moved_between_jobs_fails(self):
        def f(cv):
            cv["experience"][0]["bullets"][0] = "Grew the merchant base to 250,000 monthly active users."
        rep = run_cv(mutated("cv-nl.json", f))
        self.assertIn("belongs to another part", msgs(rep))

    def test_invented_company_fails(self):
        rep = run_cv(mutated("cv-nl.json", lambda cv: cv["experience"][1].update(company="Acme Global")))
        self.assertIn("not in your work history", msgs(rep))

    def test_inflated_title_fails(self):
        rep = run_cv(mutated("cv-nl.json", lambda cv: cv["experience"][0].update(title="Head of Product")))
        self.assertIn("differs from my-facts", msgs(rep))

    def test_wrong_dates_fail(self):
        rep = run_cv(mutated("cv-nl.json", lambda cv: cv["experience"][1].update(dates="01/2018 – 03/2022")))
        self.assertIn("dates", msgs(rep))

    def test_invented_skill_fails(self):
        rep = run_cv(mutated("cv-nl.json", lambda cv: cv["skills"].append("Python")))
        self.assertIn('skill "Python"', msgs(rep))

    def test_invented_tool_in_bullet_fails(self):
        def f(cv):
            cv["experience"][2]["bullets"][0] = "Built weekly sales dashboards in Tableau for 45 store managers."
        self.assertIn('"Tableau"', msgs(run_cv(mutated("cv-nl.json", f))))

    def test_never_claim_phrase_and_regex_fail(self):
        def f(cv):
            cv["summary"] = "Product manager and people manager with 9 years in payments."
            cv["experience"][0]["bullets"][0] = "Took full P&L ownership of checkout; drop-off fell from 38% to 24%."
        m = msgs(run_cv(mutated("cv-nl.json", f)))
        self.assertIn("people manager", m)
        self.assertIn("P&L ownership", m)

    def test_fluff_fails(self):
        def f(cv):
            cv["experience"][0]["bullets"][2] = "Spearheaded a subscription billing product for 1,200 SMB merchants in 5 months."
        self.assertIn("fluff", msgs(run_cv(mutated("cv-nl.json", f))))

    def test_salary_on_cv_fails(self):
        self.assertIn("salary", msgs(run_cv(mutated("cv-nl.json", lambda cv: cv.update(additional=["Current CTC 28 LPA"])))))

    def test_headline_title_and_tag_must_be_real(self):
        m = msgs(run_cv(mutated("cv-nl.json", lambda cv: cv.update(headline="Director of Product | Payments · Blockchain"))))
        self.assertIn("headline title", m)
        self.assertIn("Blockchain", m)

    def test_language_level_cannot_be_inflated(self):
        def f(cv):
            cv["languages"] = ["English (C1)", "German (B2)"]
        self.assertIn("german level", msgs(run_cv(mutated("cv-nl.json", f))).lower())

    def test_education_and_certification_must_match(self):
        def f(cv):
            cv["education"] = ["MBA, Pune University, 2019"]
            cv["certifications"].append("PMP, PMI, 2022")
        m = msgs(run_cv(mutated("cv-nl.json", f)))
        self.assertIn("Education", m)
        self.assertIn("Certification", m)

    def test_contact_and_visa_line_must_match_facts(self):
        def f(cv):
            cv["contact"]["email"] = "someone.else@example.com"
            cv["personal"]["needs_visa"] = False
        m = msgs(run_cv(mutated("cv-nl.json", f)))
        self.assertIn("email", m)
        self.assertIn("needs_visa", m)

    def test_photo_rules(self):
        nl = run_cv(mutated("cv-nl.json", lambda cv: cv["options"].update(include_photo=True)))
        self.assertIn("no photo", msgs(nl))
        de = run_cv(mutated("cv-nl.json", lambda cv: (cv.update(country="DE"), cv["options"].update(include_photo=True))))
        self.assertNotIn("no photo", msgs(de))
        self.assertTrue(any("photo is optional" in w["msg"] for w in de.warnings))

    def test_summary_word_limit(self):
        long = "Product manager with 9 years across payments, edtech and retail tech. " * 6
        self.assertIn("summary has", msgs(run_cv(mutated("cv-nl.json", lambda cv: cv.update(summary=long)))))

    def test_bullets_without_numbers_fail_when_facts_have_numbers(self):
        def f(cv):
            for e in cv["experience"]:
                e["bullets"] = ["Worked with merchants and engineers on the product."]
            cv["projects"] = []
        self.assertIn("bullets have a number", msgs(run_cv(mutated("cv-nl.json", f))))


class LetterAndAnswers(unittest.TestCase):
    def test_letter_jd_names_need_the_jd(self):
        rep, _ = truth_check.run(FACTS, letter=fixture("letter-nl.json"))  # no JD given
        self.assertIn('"iDEAL"', msgs(rep))

    def test_letter_invented_number_and_length(self):
        def f(lt):
            lt["paragraphs"][1] = "I grew revenue by 370% in 2 years. " + " ".join(["More words here."] * 70)
        rep, _ = truth_check.run(FACTS, letter=write_tmp(mutated("letter-nl.json", f), "letter.json"), jd_path=JD_NL)
        m = msgs(rep)
        self.assertIn('number "370"', m)  # (letters match numbers against all facts, not per claim)
        self.assertIn("cover letter has", m)

    def test_answer_word_limit(self):
        def f(a):
            a["answers"][0]["a"] = "I like merchants. " * 30
        rep, _ = truth_check.run(FACTS, answers=write_tmp(mutated("answers-nl.json", f), "answers.json"), jd_path=JD_NL)
        self.assertIn("max 80", msgs(rep))


class Parsing(unittest.TestCase):
    def test_number_forms(self):
        self.assertIn(450000.0, number_values("costing ₹4,50,000 a year"))
        self.assertIn(55000.0, number_values("₹55K saved"))
        self.assertIn(12000000.0, number_values("₹1.2 Cr revenue"))
        self.assertEqual(number_values("B2B SaaS and Web3"), set())
        self.assertEqual(number_values("04/2022"), {4.0, 2022.0})
        self.assertEqual(number_values("see https://example.com/app123 and me@example.com"), set())

    def test_salary_parsing(self):
        s = parse_salary("Salary: €68,000 – €82,000 per year")
        self.assertEqual((s["currency"], s["min"], s["max"], s["period"]), ("EUR", 68000, 82000, "year"))
        s = parse_salary("₹30 – 42 LPA fixed")
        self.assertEqual((s["currency"], s["min"], s["max"]), ("INR", 3000000, 4200000))
        s = parse_salary("AED 25,000 – 30,000 per month")
        self.assertEqual((s["currency"], s["period"]), ("AED", "month"))
        self.assertIsNone(parse_salary("We have 5 - 8 teams"))

    def test_template_comments_are_ignored(self):
        facts = load_facts(FACTS)
        self.assertEqual(facts["dob"], "")


if __name__ == "__main__":
    unittest.main()
