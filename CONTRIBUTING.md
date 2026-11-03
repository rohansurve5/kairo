# Contributing to Kairo

Thank you for helping. Kairo is small on purpose, so please open an issue first for anything bigger than a fix.

## Ground rules

- **Never invent facts.** Every CV line, number, title and date must come from the user's own facts.
- **No auto-apply.** Kairo never submits forms, logs in or sends email for the user.
- **Fake data only.** Tests and examples use the fake user Priya Sharma (`tests/fixtures/priya/`) and invented companies. Never add real people, real CVs or real contact details.
- **No third-party content.** No paid-course material, purchased lists or copied text.
- **Privacy.** The skill may send only public job data, the fit score, verdict, red flags, visa flag and status to the dashboard (see `docs/CONNECTOR-CONTRACT.md`).

## Making a change

1. Keep `skill/kairo/SKILL.md` under 500 lines. Details go in `skill/kairo/references/`.
2. If you change a rule in `references/`, check the matching script in `skill/kairo/scripts/`.
3. Run the tests and rebuild the ZIP:

   ```bash
   .venv/bin/python -m unittest discover -s tests -v
   .venv/bin/python tools/build_skill_zip.py
   python3 tools/privacy_scan.py
   ```

4. Open a pull request with a short, plain-English description of what changed and why.

The dashboard and connector server are not in this repository. For connector questions, open an issue.

By contributing, you agree that your work is released under the [MIT licence](LICENSE).
