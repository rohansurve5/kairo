# Cover letter shape

At most 250 words in the paragraphs (the greeting and sign-off are added by the script). 3 to 4 short paragraphs. Plain, specific, no filler.

| Paragraph                   | What goes in it                                                                                                                                                                                                                                |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Why them                 | One line on what the company does (from the JD or their site) and the link to the user's real work. Name the role.                                                                                                                             |
| 2. Proof one                | The strongest my-facts result that matches the JD's main need, with its real number.                                                                                                                                                           |
| 3. Proof two (+ honest gap) | A second real result for another JD need. If there is a real gap the reader will notice, one honest line on how the user would close it. Never claim the gap away.                                                                             |
| 4. Practical close          | Abroad: where they are based and that they are ready to relocate; if the company is a confirmed sponsor (NL register), one line on that. At home in another city: "based in <city>, open to relocating to <job city>". One short closing line. |

## Rules

- Numbers and names only from my-facts, or the company's own facts from the JD.
- No filler: "I am excited to apply", "I believe I would be a great fit", "To whom it may concern", "passionate", "results-driven". The truth check fails on these.
- No salary in the cover letter unless the job asks for it.
- Greeting: "Dear <Company> hiring team," unless the JD names the hiring manager.
- Sign-off: "Kind regards," and the user's name.

## letter.json

See `templates/letter.example.json`. The build script adds the header (name, headline, location, contact links), date, "Re: <role> – <company>", greeting, paragraphs and sign-off, and checks it fits on 1 page.
