# CV rules

The CV is built from my-facts only. You choose, order and lightly re-word. The script builds the PDF and the truth check enforces the facts.

## Never

- Never change a number, date, job title, company, degree or certificate.
- Never move a result from one job to another (the truth check matches numbers per job).
- Never add a tool, client, domain, skill or language level that is not in my-facts.
- Never put salary, CTC, notice period or a photo on the CV (photo: see `country-formats.md`).
- No fluff words: spearheaded, leveraged, synergy, passionate, results-driven, dynamic, go-getter, self-starter, rockstar, ninja, guru, thought leader, team player, detail-oriented, hard-working, "think outside the box", "proven track record", world-class, best-in-class, cutting-edge, game-changer. The truth check fails on these unless the phrase is in the user's own facts.

## Structure (the script lays it out)

1. Header: name, headline, location line, contact line. The location line follows the country rules automatically.
2. Professional Summary
3. Work Experience (or Projects first, if `projects_first` is true: only for people whose projects are their strongest proof)
4. Projects (optional)
5. Skills
6. Education
7. Certifications
8. Languages
9. Additional Information (optional)
10. Country extras (added automatically): Poland consent clause, Germany place-and-date line.

One column, plain text, no tables, no icons, no images: this is what applicant tracking systems (ATS) read best.

## Headline

`<Title> | <Tag> · <Tag> · <Tag>`

- Title: one of my-facts `Headline titles`, or a past job title.
- Tags: 2 to 4 of the user's real areas (strength areas or skills) that match the JD, using the JD's words where they truly fit.

## Summary (at most 60 words, 2 to 3 lines)

- Line 1: who they are, using an approved summary hook from my-facts if there is one (years and areas from my-facts).
- Line 2: the one strongest result from my-facts that matches this JD, with its real number.
- Abroad jobs: end with "Open to relocation." only if my-facts says `Open to relocation: yes`.
- Self-check: if this summary could be pasted into another person's CV unchanged, rewrite it.

## Bullets

- Shape: action, what, result. Put the result first when there is a real result.
- At most about 30 words (2 lines). The truth check warns above 40.
- At least 40% of all bullets carry a real number. If my-facts has too few numbered bullets, the check only warns: then ask the user if they have real numbers to add to my-facts.
- Most relevant bullets first in each job. Use the JD's words when they truly describe the same work.

## Jobs

- Every job in my-facts stays on the CV with at least 1 bullet (leaving one out creates a gap). Old or less relevant jobs can have 1 to 2 bullets.
- Title, company, city and dates exactly as in my-facts.

## Skills

- 10 to 18 skills, all from my-facts `Skills` (or its `Skill aliases`). JD-matching skills first.
- Use the JD's word only through an alias the user has (e.g. JD "Experimentation" when my-facts has `Experimentation = A/B testing`).

## Length

- 1 page for most people; 2 pages at most. Word range from my-facts `Rules` (default 300 to 750).
- The build script stops with exit code 3 if the PDF is longer than 2 pages: cut the least relevant bullets.

## Honest gaps

If the JD needs something the user does not have, do not hide it and do not claim it. Mention it to the user in the chat, and if useful write one honest line in the cover letter (how they would close the gap).

## cv.json fields

See `templates/cv.example.json`. Key fields:

- `country`: job country code (IN, NL, IE, DE, PL, FR, AE, SG, GB).
- `target.company`, `target.role`: used in the file name, PDF title and the Poland clause.
- `personal.home_country`, `personal.nationality`: from my-facts.
- `personal.open_to_relocation`: true only if my-facts Targets says `Open to relocation: yes`; otherwise false.
- `personal.needs_visa`: from my-facts Visa needs for this country (the truth check compares them).
- `options.include_photo`, `options.include_dob`: false unless the user asked and the country allows it.
