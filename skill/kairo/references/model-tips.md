# Model tips (the only file with model names; update names here only)

A tip is about the user's **next** step, so they can switch model before it starts. A tip that comes after the work is done is useless.

| When (the reply ends with this next step) | Tip line (copy exactly, fill nothing else in) |
|---|---|
| Job check with verdict **Apply** or **Maybe** ("Next: say 'make the pack'" or "ask the recruiter … then say 'make the pack'") | "Tip: before you say 'make the pack', switch to your strongest model (e.g. Opus) if your plan has it. It writes a better CV and letter." |
| Setup is about to start (the user said "set up Kairo" and you ask for the CV) | "Tip: use your strongest model (e.g. Opus) for setup, if your plan has it." |
| Pack delivered ("Next: after you apply, say 'applied'") | "Tip: for job checks and status updates a faster model is enough (e.g. Sonnet), and it saves your usage." |

Rules
- Put the tip line just before the "Next:" line. Each tip at most once per chat.
- Never show tips to a user on the free plan: my-facts `Claude plan: free`, or they told you so in the chat.
- Skip a tip only when you can see you are already the suggested kind of model (for example you are Opus and the tip says "strongest model"), or the user said they do not want tips. If unsure, show it.
- Never block or slow down a task because of the model in use.
