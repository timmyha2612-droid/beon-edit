# Job card

One small text file per job, written at the end of the opening grilling. Every stage skill reads it before
working, and the `job_guard` hook blocks Resolve edits in a session until one is linked and its required
lines are filled.

The template, the Kinds and the required lines per Kind are in `intake.md` §4 (one copy only). Fill every
line; write `n/a` when a line doesn't apply, never leave it blank. A line still holding a `<placeholder>`
or the template's choices (`a | b`) counts as unfilled.

## Where it goes

1. The real card: `<shoot folder>/_shotlog/jobs/<concept>.md` (small text, fine in a synced folder).
2. The session link: a copy at `~/.beon-edit/jobs/<session_id>.md`. The hook only reads this copy.
   The hook's block message prints the exact path for this session (the id isn't known in advance).
   Write the copy with the same text as the real card, plus the real card's path on the `Card:` line.

## Resuming

New session, or a second job on the same card: read the card, ask the editor "anything changed since
<Date>?" with the pop-up question tool, update the card (and its `Date:`), then write the session copy.
Don't re-run the full grilling.

Old cards (before the intake standard) may say `Grilling: done with Tim` or lack `Kind`, `Stages`,
`Delivery`: keep them, and add the missing required lines when the editor confirms the changes.
