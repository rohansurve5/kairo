# Status list and tracking

## Statuses

| Status      | Meaning                                                                                     | The user might say                                    |
| ----------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `checked`   | fit check done, verdict given                                                               | (set automatically after a job check)                 |
| `ready`     | apply pack built                                                                            | (set automatically after the pack)                    |
| `applied`   | the user applied                                                                            | "applied", "sent it", "applied yesterday"             |
| `replied`   | the company or a recruiter answered (not yet an interview): a call, a test, a questionnaire | "got a reply", "recruiter called", "they sent a test" |
| `interview` | an interview is booked or done                                                              | "interview Friday 3pm", "had the first round"         |
| `offer`     | an offer arrived                                                                            | "got an offer", "offer from X"                        |
| `rejected`  | the company said no                                                                         | "rejected", "they said no", "not moving forward"      |
| `skipped`   | the user decided not to apply                                                               | "skip", "not interested", "drop it"                   |
| `withdrawn` | the user pulled out after applying                                                          | "withdrew", "pulled out", "declined"                  |
| `on_hold`   | paused (company asked to wait, role frozen)                                                 | "on hold", "they paused the role"                     |

Usual order: checked → ready → applied → replied → interview → offer. `rejected`, `skipped`, `withdrawn` and `on_hold` can happen at any point.

## Rules

1. **One message can hold several updates** ("applied to A and B, C rejected"). Handle each.
2. **Real dates.** Turn "today", "yesterday", "last Friday", "Friday 3pm" into a real date (and time for interviews) using today's date. Status dates are `YYYY-MM-DD`.
3. **Which job?** Match by company (and title if needed) from the dashboard summary or the chat tracker. If two jobs match, show a short list and ask which one. Never guess.
4. **Short note, no private data.** A note is optional and short ("Interview Fri 6 Nov 2026, 15:00, hiring manager"). Never put salary, CTC, offer amounts or personal details in a note that goes to the dashboard. Keep those in the chat.
5. **Local candidates only.** If a form or reply says "local candidates only" or "must already hold a work permit", the status is `skipped` (or `rejected` if they said no), with that reason.
6. **"Wait before reapplying."** If a company asks the user to wait (for example 6 or 12 months), note it with the date. Later job checks for that company get the `company_hold` red flag until then.
7. **Confirm in one line per job:** `<Company> – <Title>: <old> → <new> (<date>)`.
8. **Gentle nudges** (only when asked "what is pending"): applications older than 10 days with no reply can get a short, polite follow-up that the user sends themselves.
