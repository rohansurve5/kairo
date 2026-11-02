"""Work preferences (prompt 4): contract roles, relocation, shift/night work, travel, notice.
Not open -> Skip; open -> note; not in my-facts -> never assume, ask the user. Fake user Priya only."""
import copy
import os
import unittest
from datetime import date

from helpers import FACTS, OUTPUT, SKILL, fixture, load, write_tmp

import truth_check
from form_answers import build
from jd_scan import scan
from kairo_lib import load_facts, parse_facts, read_text

TODAY = date(2026, 11, 2)
NL_JD = read_text(fixture("jd-nl-amsterdam.txt"))
CONTRACT_JD = NL_JD + "\n\nThis is a 12-month contract role with a possible extension."
SHIFT_JD = read_text(fixture("jd-in-bengaluru.txt")) + "\n\nThe role works rotational shifts, including US shift hours."


def facts_with(**lines):
    """Priya's facts with Targets preference lines replaced (value None = line removed)."""
    text = open(FACTS, encoding="utf-8").read()
    names = {"relocate": "Open to relocation", "contract": "Open to contract roles",
             "shifts": "Open to shift or night work", "travel": "Open to travel"}
    for key, value in lines.items():
        label = names[key]
        kept = [ln for ln in text.splitlines() if not ln.startswith(f"- {label}:")]
        text = "\n".join(kept)
        if value is not None:
            text = text.replace("- Score floor:", f"- {label}: {value}\n- Score floor:")
    return text


def flag(r, code):
    return [f for f in r["red_flags"] if f["code"] == code]


class JobCheck(unittest.TestCase):
    def test_contract_role_by_preference(self):
        no = scan(parse_facts(facts_with(contract="no")), CONTRACT_JD, "NL", "Product Manager", "Tulip Commerce",
                  "Amsterdam", today=TODAY)
        self.assertEqual(flag(no, "contract_role")[0]["severity"], "skip")
        self.assertEqual(no["verdict_hint"], "skip")
        yes = scan(parse_facts(facts_with(contract="yes")), CONTRACT_JD, "NL", "Product Manager", "Tulip Commerce",
                   "Amsterdam", today=TODAY)
        self.assertEqual(flag(yes, "contract_role")[0]["severity"], "note")
        unknown = scan(parse_facts(facts_with(contract=None)), CONTRACT_JD, "NL", "Product Manager", "Tulip Commerce",
                       "Amsterdam", today=TODAY)
        f = flag(unknown, "contract_role")[0]
        self.assertEqual(f["severity"], "note")
        self.assertIn("ask the user", f["text"])

    def test_shift_work_by_preference(self):
        no = scan(load_facts(FACTS), SHIFT_JD, "IN", "Product Manager", "Nirvana Ledger", "Bengaluru", today=TODAY)
        self.assertEqual(flag(no, "shift_work")[0]["severity"], "skip")
        self.assertEqual(flag(no, "shift_work")[0]["public_text"], "Shift or night work")
        yes = scan(parse_facts(facts_with(shifts="yes")), SHIFT_JD, "IN", "Product Manager", "Nirvana Ledger",
                   "Bengaluru", today=TODAY)
        self.assertEqual(flag(yes, "shift_work")[0]["severity"], "note")
        plain = scan(load_facts(FACTS), read_text(fixture("jd-in-bengaluru.txt")), "IN", "Product Manager",
                     "Nirvana Ledger", "Bengaluru", today=TODAY)
        self.assertEqual(flag(plain, "shift_work"), [])  # no false alarm on the normal JD

    def test_relocation_by_preference(self):
        no = scan(parse_facts(facts_with(relocate="no")), NL_JD, "NL", "Product Manager", "Tulip Commerce",
                  "Amsterdam", today=TODAY)
        self.assertIn("skip", {f["severity"] for f in flag(no, "location_not_target")})
        yes = scan(load_facts(FACTS), NL_JD, "NL", "Product Manager", "Tulip Commerce", "Amsterdam", today=TODAY)
        self.assertEqual(flag(yes, "location_not_target"), [])
        unknown = scan(parse_facts(facts_with(relocate=None)), NL_JD, "NL", "Product Manager", "Tulip Commerce",
                       "Amsterdam", today=TODAY)
        self.assertTrue(any("ask the user" in f["text"] for f in flag(unknown, "location_not_target")))


class FormAnswers(unittest.TestCase):
    def rows(self, facts, jd, country="NL", city="Amsterdam"):
        r = build(facts, country, jd=jd, company="Tulip Commerce", role="Product Manager", city=city)
        return dict(r["rows"]), r["flags"]

    def test_unknown_relocation_is_asked_never_assumed(self):
        rows, flags = self.rows(parse_facts(facts_with(relocate=None)), NL_JD)
        self.assertTrue(rows["Willing to relocate?"].startswith("ASK THE USER"))
        self.assertNotIn("open to relocation", rows["Current location"])
        self.assertTrue(any("relocation" in f for f in flags))

    def test_contract_shift_travel_rows_only_when_the_job_asks(self):
        rows, _ = self.rows(load_facts(FACTS), NL_JD)
        self.assertNotIn("Open to a contract / fixed-term role?", rows)
        rows, _ = self.rows(load_facts(FACTS), CONTRACT_JD + "\nTravel up to 20% across Europe.")
        self.assertEqual(rows["Open to a contract / fixed-term role?"], "No")
        self.assertTrue(rows["Willing to travel?"].startswith("ASK THE USER"))  # travel not in Priya's facts
        rows, _ = self.rows(load_facts(FACTS), SHIFT_JD, country="IN", city="Bengaluru")
        self.assertEqual(rows["Open to shift or night work?"], "No")

    def test_missing_notice_is_asked(self):
        text = "\n".join(ln for ln in open(FACTS, encoding="utf-8").read().splitlines()
                         if not ln.startswith("- Notice period:"))
        rows, _ = self.rows(parse_facts(text), NL_JD)
        self.assertTrue(rows["Notice period / earliest start"].startswith("ASK THE USER"))


class TruthCheck(unittest.TestCase):
    def letter_with(self, sentence, facts_text=None):
        L = copy.deepcopy(load("letter-nl.json"))
        L["paragraphs"][-1] = L["paragraphs"][-1] + " " + sentence
        facts_path = FACTS
        if facts_text is not None:
            facts_path = os.path.join(OUTPUT, "tmp", "facts-pref.md")
            os.makedirs(os.path.dirname(facts_path), exist_ok=True)
            open(facts_path, "w", encoding="utf-8").write(facts_text)
        rep, _ = truth_check.run(facts_path, letter=write_tmp(L, "letter-pref.json"), jd_path=fixture("jd-nl-amsterdam.txt"))
        return [i["msg"] for i in rep.errors]

    def test_baseline_letter_passes(self):
        self.assertEqual(self.letter_with(""), [])

    def test_preference_not_in_facts_fails(self):
        errs = self.letter_with("I am open to relocation to Amsterdam.", facts_with(relocate=None))
        self.assertTrue(any("does not say if you are open to relocation" in e for e in errs), errs)

    def test_preference_against_facts_fails(self):
        errs = self.letter_with("I am happy to work night shifts when needed.")
        self.assertTrue(any("NOT open to shift or night work" in e for e in errs), errs)
        errs = self.letter_with("I am open to a fixed-term contract.")
        self.assertTrue(any("NOT open to contract" in e for e in errs), errs)

    def test_preference_in_facts_passes(self):
        self.assertEqual(self.letter_with("I am open to relocating to Amsterdam."), [])

    def test_travel_claim_needs_facts(self):
        errs = self.letter_with("I am happy to travel across Europe.")
        self.assertTrue(any("open to travel" in e for e in errs), errs)


class SkillText(unittest.TestCase):
    def read(self, rel):
        return open(os.path.join(SKILL, rel), encoding="utf-8").read()

    def test_setup_asks_the_three_preferences(self):
        s = self.read("references/setup.md")
        for word in ("contract", "relocat", "shift"):
            self.assertIn(word, s.lower())
        t = self.read("templates/my-facts-template.md")
        for line in ("- Open to relocation:", "- Open to contract roles:", "- Open to shift or night work:"):
            self.assertIn(line, t)

    def test_heavy_tip_comes_before_make_the_pack(self):
        tips = self.read("references/model-tips.md")
        self.assertIn("make the pack", tips)
        skill = self.read("SKILL.md")
        shape = skill[skill.index("Reply in this shape"):skill.index("7. Connector step")]
        self.assertIn("Tip", shape)  # the job-check reply has a slot for the tip line, before "Next:"
        self.assertLess(shape.index("Tip"), shape.index("Next:"))

    def test_connector_points_to_the_login_url(self):
        import json
        cfg = json.loads(self.read("config.json"))
        self.assertEqual(cfg["connector_url"], "https://kairo.rohansurve.in/mcp")
        self.assertIs(cfg["launched"], False)
        c = self.read("references/connector.md")
        self.assertIn("connector_url", c)
        self.assertNotIn("secret link", c.lower())
