---
name: client-styles
description: "This skill should be used at the start of any Beon Media edit for a named client, before the opening grilling: an existing client (e.g. Namir Mikha, Arriva, Green, Simone Azzi, Beon's own shorts) or a new one (e.g. Ray White, Jack Ho, Funds Now, Prestige). Also whenever the editor says \"do it the Namir way\", \"Arriva style\", \"what's our usual for this client\", \"set up a profile for this client\", \"new client\", or finishes a client concept worth learning from. Holds one style profile per client: fixed fields (delivery, footage, Resolve project, end card, audio, subtitles, grade) plus prose rules for format, length, structure, A-roll, B-roll, audio, music, ending, grade, subtitle look and brand.\n"
metadata:
  version: "0.3.0"
---

# Client style profiles

Each client gets the same Beon system (house-rules and the stage skills) plus its own habits. The profile holds those habits so the grilling only asks what's still open. Profiles are public, in the plugin.

The editor running the job decides: they answer the questions, confirm the rules and approve the lessons. There is no separate approver.

## Two parts of a profile

- **Front matter** (top of `references/<slug>.md`, between `---` lines): the fixed fields from house-rules `references/intake.md` §2 (`slug`, `name`, `who`, `people`, `concept_types`, `footage`, `resolve`, `delivery`, `end_card`, `audio`, `subtitles`, `grade`, `language`, `brand_words`, `open_questions`). Scripts read it through `beon_config.load_client(slug)`; `bc.delivery(card)` takes aspect, resolution, fps and loudness from it.
- **Prose**: the rules with their tags and sources.

Front matter shapes (the reader is a tiny stdlib parser): `key: value`, `key: {a: 1, b: "x"}`, `key: [..]`, or `key:` followed by `  - {..}` lines. One line per value, no nested blocks, no comments. Quote any value with a comma, colon, apostrophe or bracket. After an edit, run `python3 skills/house-rules/scripts/beon_config.py show --client <slug>` and check every field came through.

Path placeholders in `footage.path_pattern`: `{root}` = one of the editor's editor.json `footage_roots`; `{dropbox}` = the editor's Dropbox entry in editor.json `synced_folders` (each editor's path differs; set `write_protected: true`); `{Month}`, `{n}`, `{street}` come from the shoot.

## Order of authority

Later wins: plugin defaults < client profile < shoot (`shotlog.json` `shoot`) < job card < what the editor says on this job. The brief sits with the job card.

When the profile and a stage skill disagree, the profile wins for that client. When the brief and the profile disagree, follow the brief and ask the editor whether the profile should change.

## Using a profile

1. At the start of the job, read `references/<slug>.md`. The job card `Client:` line holds the slug.
2. In the house-rules grilling, skip what the profile answers with a confirmed tag. Ask the editor to confirm [inferred] rules that matter for this concept. Ask every front-matter field set to `ask` that this job needs, and everything in `open_questions`.
3. Write each answer back: replace the `ask` with the value, add a prose line with the editor's tag and source (e.g. `[Jess, C4, 2026-11-20]`), and remove the answered question from `open_questions` and the prose list. This is a client change: save it as in "Keeping profiles current". A one-off answer for this concept only goes on the job card, not the profile.
4. Apply the profile in every stage: length and structure in aroll-cut, coverage and speeds in broll, the template and per-client habits in colour-grade, music, end card and delivery in finish-pass, and the caption look in subtitles (Step 0: profile, then the project's other timelines, then the editor; always confirmed with them).
5. Mention in the report which profile rules were applied and anything that broke from them.

## New client

1. Copy `references/_template.md` to `references/<slug>.md` (lowercase, hyphens).
2. Fill what the brief says; leave the rest `ask` and ask the editor at the grilling. The template's delivery is the Beon default (9:16 1080x1920 24p): confirm it.
3. Add the client to the table below and save as in "Keeping profiles current".

## Tags

- [Tim], [<editor name>]: that editor said it or confirmed it. Apply without asking. Keep the name: it's provenance.
- [inferred]: measured from one or more finished edits but not confirmed. Apply as a default, and ask when it matters.
- ask: unknown, ask the editor in the grilling.
- Give each rule its source (concept and date), e.g. "(C7, 15 Oct 2026)".
- Front matter `grade.template_still: default` = the house template from colour-grade.

## Keeping profiles current

- After the editor finishes a concept, the learner agent turns the numbers from the final (length, speech time, coverage, speeds, grade values, music timings, end card) into client lessons; they reach the profile only after the editor's yes (learn-from-tim).
- A rule seen in two or more finals with no counter-example can be marked [inferred, repeated]. Only an editor's word makes it a confirmed tag.
- The same rule in two or more client profiles with no counter-example in the others: the learner agent suggests it as a general rule (`lessons.py repeats`); the editor decides (Q17).
- Client lessons reach a profile only through learn-from-tim: logged in the job's lessons inbox, proposed by the learner, approved by the editor.
- Saving a client change: the plugin owner (`editor.json` `plugin_owner: true`) commits and pushes to `main`. Any other editor opens a pull request to the plugin repo (`gh pr create`); it changes nothing until Tim merges it. Concept-only lessons go in the job card's "Concept-only notes", never here.
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
