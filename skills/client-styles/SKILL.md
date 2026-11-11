---
name: client-styles
description: "This skill should be used at the start of any Beon Media edit for a named client (Namir Mikha, Arriva, Green, Beon's own shorts, Ray White, Jack Ho, Funds Now, Prestige, or a new one), before the opening grilling, and whenever Tim says \"do it the Namir way\", \"Arriva style\", \"what's our usual for this client\", \"set up a profile for this client\" or finishes a client concept worth learning from. Holds one style profile per client: format, length, structure, A-roll, B-roll, audio, music, ending, grade, subtitle look, brand rules and where the footage lives.\n"
metadata:
  version: "0.2.1"
---

# Client style profiles

Each client gets the same Beon system (house-rules and the stage skills) plus its own habits. The profile holds those habits so the grilling only asks what's still open.

## Order of authority

1. The brief and what Tim says on this job.
2. The client profile (`references/<client>.md`).
3. The house defaults in the stage skills.

When the profile and a stage skill disagree, the profile wins for that client. When the brief and the profile disagree, follow the brief and ask whether the profile should change.

## Using a profile

1. At the start of the job, read `references/<client>.md`. If there's none, copy `references/_template.md` and fill in what the brief says.
2. In the house-rules grilling, skip questions the profile answers with a [Tim] rule. Confirm [inferred] rules that matter for this concept. Ask about anything marked "ask".
3. Apply the profile in every stage: length and structure in aroll-cut, coverage and speeds in broll, the template and per-client habits in colour-grade, music, end card and delivery in finish-pass, and the caption look in subtitles (Step 0: profile, then the project's other timelines, then Tim; always confirmed with him).
4. Mention in the report which profile rules were applied and anything that broke from them.

## Tags

- [Tim]: Tim said it, or confirmed it. Apply without asking.
- [inferred]: measured from one or more of Tim's finished edits but not confirmed. Apply as a default, and ask when it matters.
- ask: unknown, ask Tim in the grilling.
- Give each rule its source (concept and date), e.g. "(C7, 15 Oct 2026)".

## Keeping profiles current

- After Tim finishes a concept, the learner agent turns the numbers from his final (length, speech time, coverage, speeds, grade values, music timings, end card) into client lessons; they reach the profile only after Tim's yes (learn-from-tim).
- A rule seen in two or more of Tim's finals with no counter-example can be marked [inferred, repeated]. Only Tim's word makes it [Tim].
- The same rule in two or more client profiles with no counter-example in the others: the learner agent suggests it as a general rule (`lessons.py repeats`); Tim decides (Q17).
- Client lessons reach a profile only through learn-from-tim: logged in the job's lessons inbox, proposed by the learner, approved by Tim.
- Keep each profile short, one line per rule. Put long analyses in the project docs and link the doc name.
- Never write client footage, stills or renders into the plugin. Profiles are text only.

## Profiles

| Client | File | State |
|---|---|---|
| Namir Mikha (real estate agent) | `references/namir-mikha.md` | C6, C1, C7 learned |
| Arriva (apartment building, Strathfield) | `references/arriva.md` | Oct C1/C3 first cut; grades read from C2, Sep C3, C4 |
| Green Real Estate (West Ryde) | `references/green.md` | Oct shoot 2 C3 learned |
| Simone Azzi (real estate agent) | `references/simone-azzi.md` | Nov C03a–d v2 learned (context-first, motivated framing, Text+ captions) |
| Beon Media (own SEO shorts, HERO) | `references/beon.md` | Subtitle looks from the SEO shorts and C1 HERO |
| Ray White, Jack Ho, Funds Now, Prestige | none yet | Start from `_template.md` on the first job |
