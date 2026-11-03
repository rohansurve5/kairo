# Kairo: guide for Claude Code sessions

Kairo is a free, open-source (MIT) job-search partner used inside Claude.ai. No coding for the user.

- **Part A (built):** a Claude.ai skill (`skill/kairo/`, shipped as `dist/kairo-skill.zip`). It does all AI work in the user's own Claude.
- **Part B:** the optional dashboard + MCP connector live in the PRIVATE sibling repo `../kairo-cloud` (server code, data model and duplicate check are not in this repo). **The server uses zero AI.**

## Safety rules (read first)

- The sibling folder `../job-autopilot.` (name ends with a dot) is the maintainer's live job system. **Read-only.** Never create, edit, move or delete anything there; never run its scripts. Read it only to port rules and logic.
- Never copy the maintainer's personal data into Kairo: name, contacts, jobs, bullets, salary, CVs, family, coach material, agencies, `data/`, `dashboard.html`, `.env`. No third-party content (paid-coach material, purchased directory lists, copied design notes). Geist font (OFL) is allowed.
- Tests use only the fake user **Priya Sharma** (`tests/fixtures/priya/`) and invented companies.
- No auto-apply, ever. Never invent facts. Local work only unless the maintainer asks: no pushes, no online accounts.

## Locked decisions

See `docs/DECISIONS.md` (9 locked decisions + build decisions + verified facts). Do not change them without the maintainer.

## Folder map

```
CLAUDE.md                  this guide
README.md                  public readme (screenshots in docs/images/, fake data only)
CONTRIBUTING.md            how to contribute
SECURITY.md                how to report a security problem
CHANGELOG.md               release notes (v1.0.0 = launch)
LICENSE                    MIT
docs/DECISIONS.md          skill decisions and verified facts (server decisions are private)
docs/CONNECTOR-CONTRACT.md MCP tools the skill calls (identical copy in ../kairo-cloud)
skill/kairo/               the Claude.ai skill (folder name = skill name)
  SKILL.md                 entry point (frontmatter: name, description <= 200 chars, license)
  references/              setup, fit, visa, CV, country formats, form answers, status, connector
  templates/               my-facts template, cover letter shape, JSON input examples
  scripts/                 kairo_lib.py, truth_check.py, jd_scan.py, form_answers.py, build_cv_pdf.py
  assets/fonts/            Geist Regular/Bold + OFL licence
tests/                     unittest suite + fake user fixtures + flow runner
tools/build_skill_zip.py   builds and validates dist/kairo-skill.zip
dist/kairo-skill.zip       the file users upload in Claude.ai (Customize > Skills)
```

## Commands

```bash
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python reportlab pypdf python-docx
.venv/bin/python -m unittest discover -s tests -v      # all tests
.venv/bin/python tests/run_flow.py                     # full flow on the fake user -> tests/output/
.venv/bin/python tools/build_skill_zip.py              # build + validate dist/kairo-skill.zip
```

Scripts must run on Python 3.9+ with only the standard library, except `build_cv_pdf.py` (reportlab; falls back to python-docx, then HTML).

## When changing the skill

- Keep `SKILL.md` short (under 500 lines); details go in `references/`.
- If a rule changes in `references/*.md`, check the matching script (country rules live in both `references/country-formats.md` and `build_cv_pdf.py` / `truth_check.py`).
- The connector contract is shared with `../kairo-cloud`: change both copies of `docs/CONNECTOR-CONTRACT.md` and `skill/kairo/references/connector.md` together.
- This repo becomes PUBLIC on launch day: no server code, no data-model internals, no secrets, no personal data (`tools/privacy_scan.py`).
- Rebuild the ZIP and run all tests after every change.
