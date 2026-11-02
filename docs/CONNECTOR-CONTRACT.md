# Kairo connector contract (v1.1)

The Kairo skill calls these MCP tools on the Kairo server. This file is kept **identical** in both repositories (`kairo` and `kairo-cloud`). Change both copies and the skill's `references/connector.md` together.

## Basics

| Item             | Value                                                                                                                                                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Endpoint         | `https://<production host>/mcp/<token>`: remote MCP server, Streamable HTTP, stateless, JSON responses                                                                                                              |
| Auth (V1)        | Secret link. The token in the URL works like a password. The server stores only its SHA-256 hash. A new link can be made at any time; the old one stops working at once.                                            |
| AI on the server | None. The server validates, checks for duplicates, stores and returns data.                                                                                                                                         |
| Dates            | `event_date` and `posted_at` are `YYYY-MM-DD` (the user's local date, sent by Claude).                                                                                                                              |
| Limits           | Request body ≤ 64 KB; `jd_text` ≤ 30,000 characters; about 120 calls per link per hour.                                                                                                                             |
| Errors           | Tool error whose text is JSON: `{"error": "<code>", "message": "<plain English>", "details": {...}}`. Codes: `invalid_input`, `not_found`, `ambiguous`, `rate_limited`, `server_error`. A wrong link gets HTTP 404. |
| Version          | Every result has `"contract": "kairo-connector/1.1"`.                                                                                                                                                               |

### Privacy rule

The server stores only public job data, the fit score, verdict, red flags (code + short public text), visa flag, the public visa proof, and status changes with dates. The skill never sends CV text, my-facts, salary tables, salary answers, CTC, cover letters, form answers, the "why" reasons or personal details. Unknown fields are rejected, so private fields cannot slip in. `red_flags[].text` is at most 140 characters and may not contain an email address or phone number.

## Enums

```text
status        = checked | ready | applied | replied | interview | offer | rejected | skipped | withdrawn | on_hold
verdict       = apply | maybe | skip
visa_flag     = yes | no | unknown | not_needed
work_mode     = onsite | hybrid | remote | unknown
source        = linkedin | naukri | indeed | greenhouse | lever | workday | ashby | smartrecruiters | company_site | other
salary.period = year | month | hour
red_flag.code = years_above | years_below | must_have_missing | language_required | jd_not_english
              | salary_below_floor | no_sponsorship | local_only | visa_unknown | sponsor_not_found
              | remote_region | location_not_target | seniority_mismatch | title_mismatch
              | specialised_domain | contract_role | agency_post | stale_posting | notice_too_long
              | company_hold | other
country_code  = ISO 3166-1 alpha-2, upper case (IN, NL, IE, DE, PL, FR, AE, SG, GB, ...). "UK" is sent as "GB".
```

---

## Tool 1: `kairo_save_job`

Call after every job check. Saves the job (or finds the same job already saved) and this user's result for it.

### Input

```json
{
  "job": {
    "title": "Product Manager, Merchant Checkout",
    "company": "Tulip Commerce B.V.",
    "company_website": "https://tulip.example",
    "country_code": "NL",
    "city": "Amsterdam",
    "work_mode": "hybrid",
    "job_url": "https://www.linkedin.com/jobs/view/1234567890/",
    "source": "linkedin",
    "posted_at": "2026-10-25",
    "experience_asked": "5+ years",
    "salary": {
      "min": 68000,
      "max": 82000,
      "currency": "EUR",
      "period": "year"
    },
    "jd_text": "Full public job description text ..."
  },
  "assessment": {
    "fit_score": 78,
    "verdict": "apply",
    "red_flags": [
      {
        "code": "notice_too_long",
        "text": "Your notice period is longer than the JD wants"
      }
    ],
    "visa_flag": "yes",
    "visa_proof": "JD: 'We are an IND recognised sponsor' (register not verified, 2026-11-02)"
  }
}
```

| Field                   | Type                               | Required | Rules                                                                                  |
| ----------------------- | ---------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| `job.title`             | string ≤ 200                       | yes      |                                                                                        |
| `job.company`           | string ≤ 200                       | yes      | as written in the JD                                                                   |
| `job.company_website`   | URL ≤ 500                          | no       | helps match the company                                                                |
| `job.country_code`      | 2 letters                          | yes      |                                                                                        |
| `job.city`              | string ≤ 100                       | no       |                                                                                        |
| `job.work_mode`         | enum                               | no       | default `unknown`                                                                      |
| `job.job_url`           | URL ≤ 2,000                        | no       | the link the user gave                                                                 |
| `job.source`            | enum                               | no       | the server re-reads it from the link when it can                                       |
| `job.posted_at`         | date                               | no       | null when unknown                                                                      |
| `job.experience_asked`  | string ≤ 40                        | no       | as in the JD, e.g. "5–8 years"                                                         |
| `job.salary`            | object                             | no       | only as posted in the JD: `min`, `max` (numbers ≥ 0), `currency` (3 letters), `period` |
| `job.jd_text`           | string, 200 to 30,000 chars        | yes      | public JD text                                                                         |
| `assessment.fit_score`  | int 0..100                         | yes      |                                                                                        |
| `assessment.verdict`    | enum                               | yes      |                                                                                        |
| `assessment.red_flags`  | array ≤ 20 of `{code, text ≤ 140}` | no       | public text only, no user numbers                                                      |
| `assessment.visa_flag`  | enum                               | yes      |                                                                                        |
| `assessment.visa_proof` | string ≤ 300                       | no       | a JD quote or a register page + date (public)                                          |

### Output

```json
{
  "contract": "kairo-connector/1.1",
  "job_id": "6f1c…",
  "application_id": "a83e…",
  "dedupe": { "result": "new", "matched_job_id": null, "overlap": null },
  "already_checked": false,
  "checked_on": "2026-11-02",
  "status": "checked",
  "status_date": "2026-11-02",
  "message": "Saved. New job."
}
```

- `dedupe.result`: `new`, `merged` (the same job was already saved; it is reused), or `maybe_duplicate` (a very similar job exists; saved as a new job and linked to it).
- `already_checked: true`: this user already has this job (one per user per job). Status and history are kept; the score, verdict and flags are updated. `message` says "Already checked on <date>, status <status>."
- A new entry starts with status `checked` dated today (server date, UTC).

---

## Tool 2: `kairo_update_status`

### Input

```json
{ "application_id": "a83e…", "status": "interview", "event_date": "2026-11-06" }
```

or, when the id is not known:

```json
{
  "job_ref": { "company": "Tulip Commerce", "title": "Product Manager" },
  "status": "applied",
  "event_date": "2026-11-03"
}
```

| Field             | Type         | Required       | Rules                                                                               |
| ----------------- | ------------ | -------------- | ----------------------------------------------------------------------------------- |
| `application_id`  | uuid         | one of the two | preferred                                                                           |
| `job_ref.company` | string ≤ 200 | one of the two | matched within this user's jobs                                                     |
| `job_ref.title`   | string ≤ 200 | no             | narrows the match                                                                   |
| `status`          | enum         | yes            |                                                                                     |
| `event_date`      | date         | yes            | a real date; at most 1 day in the future, except `interview` (up to 365 days ahead) |

### Output

```json
{
  "contract": "kairo-connector/1.1",
  "application_id": "a83e…",
  "company": "Tulip Commerce B.V.",
  "title": "Product Manager, Merchant Checkout",
  "previous_status": "applied",
  "status": "interview",
  "event_date": "2026-11-06",
  "history": [
    { "status": "checked", "event_date": "2026-11-02" },
    { "status": "interview", "event_date": "2026-11-06" }
  ],
  "message": "Tulip Commerce: applied → interview (2026-11-06)."
}
```

Errors: `not_found`; `ambiguous` with `details.candidates` (up to 10 of `{application_id, company, title, status, status_date}`). The current status is the latest event by date. Any change is allowed (users fix mistakes); the history keeps everything.

---

## Tool 3: `kairo_get_summary`

### Input

```json
{ "company": "tulip", "status": ["applied", "interview"], "limit": 20 }
```

All fields optional. `company`: contains-match, case-insensitive. `limit`: 1..100, default 20.

### Output

```json
{
  "contract": "kairo-connector/1.1",
  "counts": {
    "checked": 4,
    "ready": 2,
    "applied": 7,
    "replied": 1,
    "interview": 1,
    "offer": 0,
    "rejected": 3,
    "skipped": 5,
    "withdrawn": 0,
    "on_hold": 0
  },
  "total": 23,
  "applications": [
    {
      "application_id": "a83e…",
      "company": "Tulip Commerce B.V.",
      "title": "Product Manager, Merchant Checkout",
      "country_code": "NL",
      "fit_score": 78,
      "verdict": "apply",
      "status": "interview",
      "status_date": "2026-11-06",
      "job_url": "https://…",
      "job_is_old": false
    }
  ],
  "follow_ups_due": [
    {
      "application_id": "…",
      "company": "…",
      "title": "…",
      "applied_on": "2026-10-20",
      "days_since": 13
    }
  ]
}
```

`follow_ups_due`: status `applied` for 10+ days with no later change. `job_is_old`: the job has not been seen for 30+ days.

## Not tools

Consent, a new link, delete my data and export: web pages behind Google login (later). They are not MCP tools, so Claude can never delete data by mistake.
