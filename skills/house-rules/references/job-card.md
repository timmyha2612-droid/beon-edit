# Job card

One small text file per job, written at the end of the opening grilling. Every stage skill reads it before
working, and the `job_guard` hook blocks Resolve edits in a session until one is linked.

## Where it goes

1. The real card: `<shoot folder>/_shotlog/jobs/<concept>.md` (small text, fine in Dropbox).
2. The session link: a copy at `~/.beon-edit/jobs/<session_id>.md`. The hook only reads this copy.
   The hook's block message prints the exact path for this session (the id isn't known in advance).
   Write the copy with the same text as the real card, plus the real card's path on the `Card:` line.

New session on a job that already has a card: read the card, ask Tim "anything changed since <date>?"
with the pop-up question tool, update the card, then write the session copy. Don't re-run the full grilling.

## Template

```markdown
# Job: <client> <concept>
Card: <path to the real card in _shotlog/jobs/>
Kind: concept | footage-sort | subtitles-only | grade-only | fix
Editor: Tim | <name of the editor running this job>
Client: <client profile name, e.g. namir-mikha>
Lessons inbox: <shoot>/_shotlog/lessons/<concept>.jsonl
Date: <YYYY-MM-DD>
Grilling: done with Tim | skipped (Tim said "<his words>")

## Answers
- Client profile: <references/<client>.md, or "none yet">
- Concept and goal: 
- Target length: 
- Story beats / answers to use: 
- Jokes or light moments: on camera | B-roll allowed
- Goofy or playful people shots: allowed | not
- Camera / multicam: 
- Music: Tim adds | Claude helps | break planned at 
- Subtitles: style source (profile | timeline "<name>" | Tim styled one) and the look in plain words, confirmed by Tim
- Don't move: <anything Tim already placed>
- Footage Prep: shoot "<name>" in the app | not available (fallback: ingest.py)

## Concept-only notes
- Rules that apply to this concept only (never copied into the plugin).
```

Fill every line. Write "n/a" when a line doesn't apply to the kind of job (a footage sort has no story
beats), never leave it blank. The hook checks that the card has a `Grilling:` line and no empty
`Concept and goal:` / `Target length:` lines on concept jobs.
