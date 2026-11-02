# Fit rules: score, verdict, reasons, red flags

The script `scripts/jd_scan.py` finds signals. You read the whole JD and decide. Never raise a score just to pass the floor. Fewer good applications beat many weak ones.

## 1. Score (0 to 100)

1. Start from the script's **baseline score**. It is: 30 + matched strengths from my-facts (weighted, capped) + title match (up to 10) + years fit (0, 4 or 8).
2. Adjust by **at most 15 points**, up or down, for real fit you can see in the full JD. Say why in one line. Examples:
   - up: the JD's core problem is exactly what a my-facts bullet shows (same domain, same kind of user, same result type);
   - down: the core of the role is a domain or skill the user has never done; a big part of the JD is outside my-facts.
3. Do not count the same evidence twice.

## 2. Must-have rule

Check every line the script lists under "requirement lines" (and any other "must", "required", "minimum" line) against my-facts.

- A **required** qualification the user does not have (a degree, a certificate, a domain the role is built on, a language, a location, a level clearly above them) = red flag `must_have_missing`, blocking.
- "Nice to have", "preferred", "a plus", "bonus" = not blocking. Mention it only if it matters.
- Never treat a must-have as met because the user "could learn it".

## 3. Red flags

The script flags these. Confirm each one by reading the JD. You may clear a flag only when the JD clearly says otherwise; quote the line.

| Code                  | Blocking?                     | Meaning                                                                                                                        |
| --------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `years_above`         | yes if 3+ years over, else no | JD asks more years than my-facts "Total experience"                                                                            |
| `years_below`         | no                            | JD is clearly junior for the user                                                                                              |
| `must_have_missing`   | yes                           | a required qualification is missing (you add this one)                                                                         |
| `language_required`   | yes                           | JD requires a language the user lacks at B2 or above                                                                           |
| `jd_not_english`      | no                            | JD written in another language (often means that language is needed)                                                           |
| `salary_below_floor`  | yes                           | posted maximum is below the user's minimum for that country                                                                    |
| `no_sponsorship`      | yes, when a visa is needed    | JD says no visa sponsorship / must already have the right to work                                                              |
| `local_only`          | yes, when a visa is needed    | "local candidates only", "must already hold a residence visa"                                                                  |
| `visa_unknown`        | see visa rules                | JD silent on visa; run the visa check                                                                                          |
| `sponsor_not_found`   | see visa rules                | company not found on the official sponsor register (you add this one)                                                          |
| `remote_region`       | yes when a visa is needed     | remote job limited to a region the user is not in                                                                              |
| `location_not_target` | no                            | country not in the user's targets                                                                                              |
| `seniority_mismatch`  | no                            | level above or below the user's target roles                                                                                   |
| `title_mismatch`      | no                            | title does not match the target roles                                                                                          |
| `specialised_domain`  | no (check must-haves)         | title names a specialised domain the strengths do not cover                                                                    |
| `contract_role`       | no                            | fixed-term or contract role (often cannot support a work visa)                                                                 |
| `agency_post`         | no                            | employer not named                                                                                                             |
| `stale_posting`       | no                            | older than 30 days on a company page, 21 days on a job board at home, 10 days on a job board abroad; may be filled or a repost |
| `notice_too_long`     | no                            | JD wants a shorter notice period than the user's                                                                               |
| `company_hold`        | yes                           | the user said this company asked them to wait before reapplying (until that date)                                              |

Also check, from the connector summary or the chat tracker:

- **One role per company.** If the user already has an active application at this company, say so (applying to several roles at one employer can look unfocused). Not blocking.
- **Already checked.** If this exact job was checked before, say when and its status.

## 4. Verdict: Apply or Skip

- **Apply** = final score at or above the user's score floor (my-facts `Score floor`, default 60) **and** no blocking red flag left.
- **Skip** = anything else.
- The user can say "apply anyway". Then continue, and keep the flags in your reply.

## 5. Three reasons

Exactly 3 short lines.

- **Apply:** each reason pairs a JD need with a real my-facts fact ("JD wants subscription billing; you launched it for 1,200 SMB merchants in 5 months"). Numbers only from my-facts or the JD.
- **Skip:** the 3 strongest reasons not to apply, most important first.
- Never claim anything my-facts does not say.

## 6. Freshness and the posting date

- Use the date on the company's own careers page when you can see it; job boards often show reposts as new.
- Unknown date: write "date unknown". Do not guess.

## 7. Salary line

If the JD shows a salary, show it and the answer the user would give (from `scripts/form_answers.py` or the rule in `references/form-answers.md`). If the posted maximum is below the user's minimum, that is the `salary_below_floor` flag.

## 8. What goes to the dashboard

Only: job details from the JD, the final score, the verdict, the red flag codes with short public text (no user numbers: write "Posted salary is below your minimum", never the minimum itself), the visa flag and the public visa proof. The 3 reasons stay in the chat because they contain CV facts.
