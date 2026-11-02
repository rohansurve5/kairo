# Setup: make my-facts.md (once)

Goal: one file, `my-facts.md`, that holds only true facts about the user. Every later step reads it. Kairo's scripts parse it, so it must follow `templates/my-facts-template.md` exactly (same headings, same line formats).

## Step 1. Read the CV

The user uploads a CV (PDF, Word or text) or pastes it. Read all of it. Note: name, contact details, every job (title, company, city, start and end month), every bullet, projects, education, certifications, skills, languages.

Do not fix, round or improve anything. If two dates clash or a line is unclear, ask about it in step 2.

## Step 2. Ask at most 10 questions, in one message

Ask only what the CV does not already answer. Number the questions. Give a short example for each. Typical list:

1. **Target roles.** Which job titles? (e.g. Product Manager, Senior Product Manager)
2. **Countries and cities.** Where do you want to work? (India, Netherlands, Ireland, Germany, Poland, France, UAE, Singapore, UK, other) Open to relocating?
3. **Salary per country.** For each country: what you would ask for, and the lowest you would accept. India: also your current CTC (fixed + variable).
4. **Notice period.** How soon can you start? (e.g. 60 days, can be bought out)
5. **Visa.** Your citizenship, and any work permits you already hold.
6. **Languages.** Each language and level (A1 to C2, or Native).
7. **Never claim.** Anything that must never appear (e.g. "never say I managed people", "no MBA"). Anything in this CV that is outdated or wrong?
8. **Deal-breakers.** Company types or domains to avoid (e.g. IT services, crypto, contract roles).
9. **Contact details for the CV.** Confirm email, phone, LinkedIn, website.
10. **Missing facts.** Only if needed: a missing month, an unclear number.

Keep the message short. If the user skips a question, use a safe default and say which.

## Step 3. Write my-facts.md

Fill `templates/my-facts-template.md`. Rules:

- **Work history:** one `### Title | Company | City, Country | MM/YYYY – MM/YYYY` heading per job, newest first; `Present` for the current job. Copy bullets from the CV. You may split a long bullet in two, but keep every number, name and date exactly as the user wrote it.
- **Headline titles:** only titles the user has held, or targets the user confirms they truly work at.
- **Skills:** only skills shown in the CV or confirmed by the user. Comma-separated lines are fine.
- **Skill aliases:** add common JD words that mean the same as one of the user's skills (e.g. `Experimentation = A/B testing`).
- **Strengths for fit scoring:** 4 to 8 areas the CV proves, each with a weight (10 = strongest) and the words a job description would use. Area names must be real (they may appear as CV headline tags).
- **Salary table:** one row per target country. Expected and Minimum as plain numbers. Unit from: `LPA`, `EUR/year`, `GBP/year`, `USD/year`, `AED/month`, `SGD/month`, `PLN/month`. If the user needs a work visa there, check the current official salary minimum for that visa (`references/visa-sponsor-rules.md`) and tell the user if their Minimum is below it. Write the check date in the Note column.
- **Visa needs:** one line per target country outside the home country, starting with `needs` or `not needed`.
- **Never claim:** one line each, `"phrase" — why` or `/regex/ — why`. Add the user's items. Keep them short phrases that would really appear in a CV.
- **Total experience (years):** a whole number the user agrees with.
- **Date of birth:** leave it out unless the user asks for it (only used on German or UAE CVs, and off by default).

## Step 4. Check the file

Save it as `/tmp/kairo/my-facts.md` and run:

`python3 scripts/truth_check.py --facts /tmp/kairo/my-facts.md --lint`

Fix every FAIL line. Ask the user about warnings that need their input (for example a missing salary row).

## Step 5. Give it to the user, with exact steps

Save it to `/mnt/user-data/outputs/my-facts.md` (or offer it as a file to download). Then say, in plain words:

> Your facts file is ready. Do this once:
>
> 1. In Claude, open **Projects** and create a project called **Kairo job search**.
> 2. In that project, add **my-facts.md** to the project knowledge (the files area of the project).
> 3. Start every job chat inside this project, so I always have your facts.
> 4. When something changes (new job, new salary), say "update my facts". I will give you a new file; replace the old one.
>
> Your CV, facts and salary stay in your Claude project. The optional Kairo dashboard only stores job details, scores and statuses.

Show a short summary table: jobs found, skills, target countries, salary rows, never-claim lines. Do not paste the whole file in the chat unless asked.

## Updating facts later

When the user says "update my facts" or shares a new fact: add it in the right section, keep everything else exactly the same, update `Last updated`, run the lint check, and give the new file with the same 4 steps (replace the old file).
