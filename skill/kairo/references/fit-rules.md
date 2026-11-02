# Fit rules: score, verdict, reasons, red flags

The script `scripts/jd_scan.py` finds signals and gives a `verdict_hint`. You read the whole JD and decide. Never raise a score just to pass the floor. Fewer good applications beat many weak ones.

## 1. Score (0 to 100)

1. Start from the script's **baseline score**: 30 + matched strengths from my-facts (weighted, capped) + title match (up to 10) + years fit (0, 4 or 8).
2. Adjust by **at most 15 points**, up or down, for real fit you can see in the full JD. Say why in one line. Up: the JD's core problem is exactly what a my-facts bullet shows. Down: the core of the role is a domain or skill the user has never done.
3. Do not count the same evidence twice.

## 2. Must-have rule

Check every line the script lists under "requirement lines" (and any other "must", "required", "minimum" line) against my-facts.

- A **required** qualification the user does not have (a degree, a certificate, a domain the role is built on, a language, a level clearly above them) = red flag `must_have_missing` → **Skip**.
- "Nice to have", "preferred", "a plus", "bonus" = not a must-have.
- Never treat a must-have as met because the user "could learn it".

## 3. Red flags and what they do

The script tags each flag `skip`, `maybe` or `note`. Confirm each one by reading the JD. You may clear a flag only when the JD clearly says otherwise; quote the line.

| Code                                                                                                                                                                                     | Effect                                         | Meaning                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------- |
| `must_have_missing`                                                                                                                                                                      | Skip                                           | a required qualification is missing (you add this one)                           |
| `years_above`                                                                                                                                                                            | Skip if 3+ years over (a must-have), else note | JD asks more years than my-facts "Total experience"                              |
| `language_required`                                                                                                                                                                      | Skip (a must-have)                             | JD requires a language the user lacks at B2 or above                             |
| `no_sponsorship`                                                                                                                                                                         | Skip, when a visa is needed                    | JD clearly says no visa sponsorship / must already have the right to work        |
| `local_only`                                                                                                                                                                             | Skip, when a visa is needed                    | "local candidates only", "must already hold a residence visa"                    |
| `remote_region`                                                                                                                                                                          | Skip when a visa is needed, else note          | remote job limited to a region the user is not in                                |
| `company_hold`                                                                                                                                                                           | Skip                                           | the user said this company asked them to wait (until that date)                  |
| `visa_unknown`                                                                                                                                                                           | Maybe                                          | visa needed and the JD is silent or unclear: ask the recruiter                   |
| `sponsor_not_found`                                                                                                                                                                      | Maybe                                          | not found on the official sponsor register (you add this one): ask the recruiter |
| `salary_below_floor`                                                                                                                                                                     | Maybe                                          | posted maximum is below the user's minimum: ask whether the budget can reach it  |
| `years_below`, `jd_not_english`, `location_not_target`, `seniority_mismatch`, `title_mismatch`, `specialised_domain`, `contract_role`, `agency_post`, `stale_posting`, `notice_too_long` | note                                           | worth saying; not a verdict on its own                                           |

Also check, from the connector summary or the chat tracker:

- **One role per company.** If the user already has an active application at this company, say so (several roles at one employer can look unfocused). A note.
- **Already checked.** If this exact job was checked before, say when and its status.

## 4. Verdict: Apply, Maybe or Skip

- **Skip** only when: the job clearly says no sponsorship or local candidates only (and the user needs a visa), a must-have is missing, or the final score is under the user's score floor (my-facts `Score floor`, default 60).
- **Maybe** when: none of the Skip reasons apply, but visa or sponsorship is unclear (or the posted salary is under the user's floor). Tell the user exactly what to ask the recruiter.
- **Apply** otherwise.
- The user can say "apply anyway" after Skip or Maybe. Then continue, and keep the flags in your reply.

## 5. Three reasons

Exactly 3 short lines.

- **Apply:** each reason pairs a JD need with a real my-facts fact ("JD wants subscription billing; you launched it for 1,200 SMB merchants in 5 months"). Numbers only from my-facts or the JD.
- **Maybe:** 2 reasons it fits, then the open question for the recruiter.
- **Skip:** the 3 strongest reasons not to apply, most important first.
- Never claim anything my-facts does not say.

## 6. Freshness and the posting date

- Use the date on the company's own careers page when you can see it; job boards often show reposts as new.
- Unknown date: write "date unknown". Do not guess.

## 7. Salary line

If the JD shows a salary, show it and the answer the user would give (from `scripts/form_answers.py`). If my-facts has no salary ask or floor for that country, write "I need your salary ask for <country>" and ask; never estimate.

## 8. What goes to the dashboard

Only: job details from the JD, the final score, the verdict (`apply`, `maybe` or `skip`), the red flag codes with short public text (no user numbers: write "Posted salary is below your minimum", never the minimum itself), the visa flag and the public visa proof. The 3 reasons stay in the chat because they contain CV facts.
