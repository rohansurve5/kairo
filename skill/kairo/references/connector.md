# Kairo connector (dashboard) and the chat tracker

The Kairo dashboard (kairo.rohansurve.in) is optional and free. The user adds it in Claude as a custom connector. Its server uses no AI and stores only public job data, scores, verdicts, red flags, visa flags and status history. The full contract is in the Kairo repository (`docs/CONNECTOR-CONTRACT.md`); this page is what you need.

## Is it connected?

The connector is available when you can see tools named `kairo_save_job`, `kairo_update_status` and `kairo_get_summary`. If you cannot see them, use the chat tracker (below).

## What may be sent (and what never)

| Send                                                                                                                                                                                                                                         | Never send                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| job title, company, company website, country code, city, work mode, job link, apply link, source, posting date, seniority, years asked, languages required, the posted salary as written in the JD, the JD's own visa text, the full JD text | the CV or any CV line, my-facts lines, the user's salary table, current or expected salary or CTC, cover letters, form answers, the 3 fit reasons, phone, email, date of birth, nationality, anything else personal |
| fit score, verdict (`apply` / `skip`), red flag codes with short public text, visa flag, public visa proof (JD quote or register page + date)                                                                                                | red flag text that contains the user's numbers (write "Posted salary is below your minimum", never the minimum)                                                                                                     |
| status, status date, a short note without private data                                                                                                                                                                                       | offer amounts, salary talks, personal notes                                                                                                                                                                         |

## When to call

| After                                                     | Call                  | Fields                                                                                          |
| --------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------- |
| a job check (flow 2)                                      | `kairo_save_job`      | `job` (public JD data), `assessment` (fit_score, verdict, red_flags, visa_flag, visa_proof)     |
| an apply pack (flow 3)                                    | `kairo_update_status` | `application_id`, `status: "ready"`, `event_date`                                               |
| a status message (flow 4)                                 | `kairo_update_status` | `application_id` (or `job_ref` with company and title), `status`, `event_date`, optional `note` |
| "my jobs", "what is pending", or to find a job by company | `kairo_get_summary`   | optional `company`, `status`, `limit`                                                           |

Keep the `application_id` that `kairo_save_job` returns in your reply context, so later status updates in the same chat can use it. In a new chat, find it with `kairo_get_summary` (filter by company).

`kairo_save_job` may answer:

- `already_tracked: true`: this user already has this job; tell them its current status and date.
- `dedupe.result: "maybe_duplicate"`: a very similar job exists; mention it in one line.

`kairo_update_status` may answer `ambiguous` with a short list: show it and ask which job.

## After a call

- Worked: end the reply with **Your dashboard is updated.**
- Failed: one line, for example "I could not update your dashboard (connection error). Here is your tracker instead." Then show the chat tracker. Never retry more than once.

## Chat tracker (when the connector is not available)

Keep one table in the chat and show it after each change, newest first:

| #   | Company        | Role                               | Country | Fit | Verdict | Status  | Date       |
| --- | -------------- | ---------------------------------- | ------- | --- | ------- | ------- | ---------- |
| 1   | Tulip Commerce | Product Manager, Merchant Checkout | NL      | 78  | Apply   | Applied | 2026-11-03 |

Add once per chat: "Tip: connect the free Kairo dashboard at kairo.rohansurve.in to keep this list in one place." The chat tracker lives only in this chat; the user can copy it into a project file if they want to keep it.
