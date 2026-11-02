# Form answers and salary

Two parts: the **standard answers** (from the script, the same facts every time) and **job-specific answers** (you write them, truth-checked).

## Standard answers

Run:
`python3 scripts/form_answers.py --facts my-facts.md --country NL --jd /tmp/kairo/jd.txt --company "..." --role "..." --city "..."`

It gives a table: name, email, phone, LinkedIn, current location (with the relocation note), nationality (abroad), "authorised to work without sponsorship?", "need sponsorship?", "willing to relocate?", notice period, total experience, languages and salary. India adds current CTC, expected CTC and notice period in days.

Show the table as it is. Do not change the facts in it. If a form asks something the table does not cover, answer only from my-facts or ask the user.

## Salary rule

1. **Missing ask or floor:** if my-facts has no salary ask or no floor for that country, the script says "ASK THE USER". Ask the user; never fill in, estimate or suggest a number.
2. **A number the user gave for this one job wins.** Pass it with `--override "EUR 80,000"`.
3. **The job post shows a range** in the same currency as the user's table: answer inside the range, 40% up from the bottom (the lower half), rounded. Example: EUR 70,000 to 80,000 gives EUR 74,000.
4. **Never below the user's minimum** for that country. If the rule gives less, use the minimum.
5. **No range, or a different currency:** use the user's expected amount from the salary table.
6. **Posted maximum below the user's minimum:** this is the `salary_below_floor` red flag. Tell the user before they apply.

Conventions, shown automatically:

- India: CTC in LPA (lakh per year), "negotiable".
- Netherlands: gross per year, excluding holiday pay.
- Germany, Ireland, France, UK: gross per year.
- Poland: gross per month (PLN).
- UAE, Singapore: per month.

The user's minimum should already be at or above any visa salary minimum (checked during setup). If the posted salary looks below a visa minimum, say so and point to the official page.

## India form style

Indian forms usually ask: current CTC (fixed + variable), expected CTC, notice period in days, "can you join immediately?", total and relevant experience in years, current and preferred locations. Use my-facts exactly. Never inflate the current CTC. If the notice period can be bought out, say so only if my-facts says so.

## Job-specific answers

- 2 to 3 answers, at most 80 words each, for the questions this job will likely ask (or the ones the user pastes).
- Typical: "Why <Company>?", "Describe a product you launched", one about the JD's main requirement.
- Facts only from my-facts; you may use the company's own facts from the JD.
- Write them to `/tmp/kairo/answers.json` (format: `templates/answers.example.json`) and run the truth check.

## Rules

- Never commit to anything the user has not said (start date, relocation date, salary flexibility).
- **Forms that forbid AI help:** if the job or form says not to use AI tools, make **only the CV**. Do not write the cover letter or any answers; tell the user to write those themselves.
- Never fill in or submit the form yourself.
