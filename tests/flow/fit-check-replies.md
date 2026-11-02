# Dry run: what Kairo replies for the 3 sample jobs

Fake user: Priya Sharma (Pune, 9 years, PM). Fictional companies. Written by Claude (Claude Code) following `skill/kairo/SKILL.md` and `references/fit-rules.md`, from the script output in `tests/output/flow/scan-*.json`. This is the AI part of flow 2; in real use Claude.ai writes it. The IND register was **not** searched (the companies are invented, and this test ran offline), so it says "not verified".

---

## 1. India: Nirvana Ledger, Product Manager – Merchant Payments (Bengaluru)

**Nirvana Ledger – Product Manager, Merchant Payments** (Bengaluru, India)
Fit: 81/100 → **Apply**
(baseline 73; +8: the role's core, subscription billing and UPI checkout for SMB merchants, is exactly your Kestrel work)
Why:

1. They want subscription billing for SMB merchants; you launched a subscription billing product for 1,200 SMB merchants in 5 months.
2. They want higher payment success; you cut checkout drop-off from 38% to 24% with a 2-step UPI and card flow.
3. They want someone who answers their own questions with data; you built SQL dashboards and grew paid conversion from 2.1% to 3.4% with A/B tests.
   Red flags: none. Note: "UPI AutoPay" (recurring mandates) is not in your facts; if asked, say what you did with UPI and that AutoPay is new to you.
   Visa: not needed.
   Salary: ₹30–42 LPA posted. Your answer: 35 LPA (negotiable). Notice: they prefer 60 days or less; yours is 60 days.
   Next: say "make the pack" for the CV, cover letter and answers.

---

## 2. Netherlands: Tulip Commerce B.V., Product Manager, Merchant Checkout (Amsterdam)

**Tulip Commerce – Product Manager, Merchant Checkout** (Amsterdam, Netherlands)
Fit: 78/100 → **Apply**
(baseline 70; +8: checkout conversion and payment success for merchants is the centre of both this role and your last 4 years)
Why:

1. They want someone to own checkout conversion; you cut checkout drop-off from 38% to 24%.
2. They want payment success with a cross-functional team; you led 6 engineers and 2 designers and payment success rose from 91% to 96%.
3. They want weekly merchant discovery; you turned 40+ merchant interviews into a 2-quarter roadmap.
   Red flags: none blocking. Dutch is "a plus, not required". iDEAL is new to you (not required).
   Visa: yes. The JD says Tulip Commerce is an IND recognised sponsor and offers highly skilled migrant sponsorship. IND register: not verified (offline test). Confirm with the recruiter.
   Salary: €68,000–€82,000 per year posted. Your answer: €74,000/year, excluding holiday pay.
   Next: say "make the pack" for the CV, cover letter and answers.

---

## 3. UAE: Falcon Retail Group, Senior Product Manager – Loyalty & CRM (Dubai)

**Falcon Retail Group – Senior Product Manager, Loyalty & CRM** (Dubai, UAE)
Fit: 39/100 → **Skip**
(baseline 44; −5: loyalty and CRM, the core of the role, are not in your facts)
Why:

1. It requires fluent Arabic; your languages are English, Hindi, Marathi and German (A2).
2. Only candidates who already hold a UAE residence visa can apply; you need an employment visa.
3. It asks for 12+ years, including 5 in retail loyalty or CRM; you have 9 years and no loyalty or CRM work.
   Red flags: language required (Arabic), local candidates only, no sponsorship, asks 3+ more years than you have.
   Visa: no. "Candidates must already hold a valid UAE residence visa."
   Salary: AED 25,000–30,000 per month posted (your answer would be AED 28,000/month, your minimum).
Next: paste the next job, or say 'apply anyway'.

---

## Connector: what `kairo_save_job` would receive for job 2 (public data only)

```json
{
  "job": {
    "title": "Product Manager, Merchant Checkout",
    "company": "Tulip Commerce B.V.",
    "country_code": "NL",
    "city": "Amsterdam",
    "work_mode": "hybrid",
    "source": "company_site",
    "posted_at": "2026-10-25",
    "posted_source": "company_page",
    "seniority": "mid",
    "experience_min": 5,
    "languages_required": [],
    "salary": {
      "text": "€68,000 – €82,000 per year",
      "min": 68000,
      "max": 82000,
      "currency": "EUR",
      "period": "year"
    },
    "visa_text": "We are an IND recognised sponsor and offer visa sponsorship (highly skilled migrant) and relocation support.",
    "jd_text": "<full public JD text>"
  },
  "assessment": {
    "fit_score": 78,
    "verdict": "apply",
    "red_flags": [],
    "visa_flag": "yes",
    "visa_proof": "JD: 'We are an IND recognised sponsor' (IND register not verified, 2026-11-02)"
  }
}
```

Not sent: the 3 reasons, Priya's salary answer (€74,000) and minimum, her CV, her contact details.

## Without the connector: the chat tracker

| #   | Company             | Role                                   | Country | Fit | Verdict | Status  | Date       |
| --- | ------------------- | -------------------------------------- | ------- | --- | ------- | ------- | ---------- |
| 3   | Falcon Retail Group | Senior Product Manager – Loyalty & CRM | AE      | 39  | Skip    | Checked | 2026-11-02 |
| 2   | Tulip Commerce      | Product Manager, Merchant Checkout     | NL      | 78  | Apply   | Checked | 2026-11-02 |
| 1   | Nirvana Ledger      | Product Manager – Merchant Payments    | IN      | 81  | Apply   | Checked | 2026-11-02 |

Tip: connect the free Kairo dashboard at kairo.rohansurve.in to keep this list in one place.
