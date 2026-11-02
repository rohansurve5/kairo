# Kairo connector (dashboard) and the chat tracker

The Kairo dashboard is optional and free. The user adds it in Claude as a custom connector (a personal secret link). Its server uses no AI and stores only public job data, scores, verdicts, red flags, visa flags and status history. Full contract: `docs/CONNECTOR-CONTRACT.md` in the Kairo repository (v1.1).

## Is it connected?

The connector is available when you can see tools named `kairo_save_job`, `kairo_update_status` and `kairo_get_summary`. If you cannot see them, use the chat tracker (below).

## What may be sent (and what never)

| Send                                                                                                                                                                                                       | Never send                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| job: title, company, company website, country code, city, work mode, the job link, source, posting date, years asked (as written), the posted salary (min, max, currency, period), the full public JD text | the CV or any CV line, my-facts lines, the salary table, the salary answer, current or expected salary or CTC, cover letters, form answers, the 3 "why" reasons, phone, email, date of birth, nationality, notes about salary talks |
| assessment: fit score, verdict (`apply`, `maybe`, `skip`), red flag codes with short public text, visa flag (`yes`, `no`, `unknown`, `not_needed`), public visa proof (JD quote, or register page + date)  | red flag text with the user's numbers (write "Posted salary is below your minimum", never the minimum)                                                                                                                              |
| status and the real status date                                                                                                                                                                            | anything else                                                                                                                                                                                                                       |

The server rejects unknown fields, so send exactly these.

## When to call

| After                                                          | Call                  | Arguments                                                                                                                                         |
| -------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| a job check (flow 2)                                           | `kairo_save_job`      | `job` {title, company, country_code, jd_text, and the optional fields above}, `assessment` {fit_score, verdict, red_flags, visa_flag, visa_proof} |
| an apply pack (flow 3)                                         | `kairo_update_status` | `application_id`, `status: "ready"`, `event_date`                                                                                                 |
| a status message (flow 4)                                      | `kairo_update_status` | `application_id` (or `job_ref` {company, title}), `status`, `event_date`                                                                          |
| "show my jobs", "what is pending", or to find a job by company | `kairo_get_summary`   | optional `company`, `status` (list), `limit`                                                                                                      |

Field notes: `country_code` is 2 capital letters ("GB" for the UK). `jd_text` is the full JD (200 to 30,000 characters; shorten only boilerplate if it is longer). `event_date` is `YYYY-MM-DD`. Keep the `application_id` from `kairo_save_job` for later status updates in the same chat; in a new chat, find it with `kairo_get_summary` (filter by company).

`kairo_save_job` answers:

- `already_checked: true` with "Already checked on <date>, status <status>": tell the user.
- `dedupe.result: "merged"`: the same job was already known (fine). `"maybe_duplicate"`: a very similar job exists; mention it in one line.

`kairo_update_status` may answer `ambiguous` with a short list: show it and ask which job.

## After a call

- Worked: the reply says **Your dashboard is updated.** (just before the next-step line).
- Failed: one line, for example "I could not update your dashboard (connection error). Here is your tracker instead." Then show the chat tracker. Retry at most once.

## Chat tracker (when the connector is not available)

Keep one table in the chat and show it after each change, newest first:

| #   | Company        | Role                               | Country | Fit | Verdict | Status  | Date       |
| --- | -------------- | ---------------------------------- | ------- | --- | ------- | ------- | ---------- |
| 1   | Tulip Commerce | Product Manager, Merchant Checkout | NL      | 78  | Maybe   | Applied | 2026-11-03 |

The chat tracker lives only in this chat; the user can copy it into a project file if they want to keep it. Dashboard invites follow the rule in `SKILL.md` section 5 (`config.json`); never add a link anywhere else.
