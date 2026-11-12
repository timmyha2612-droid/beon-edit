# Intake standard (DRAFT for review)

Everything an editor's Claude needs before it edits, in four saved files. Claude asks the questions and
writes the files; next time it reads them and only asks what changed ("anything changed since <date>?").
Beon's house rules (B-roll speeds and zoom limits, grade template, caption rules, track layout) stay
built into the skills and are never asked.

Who decides: **the editor running the job** answers every question and approves every gate. There is no
separate approver. "Tim" in older skill text means "the editor" unless a line says it is about the
plugin owner (rule changes, below).

Order of authority when two files disagree, later wins:
plugin defaults < client profile < shoot < job card < what the editor says in the session.

| # | File | Once per | Where | Who fills it |
|---|---|---|---|---|
| 1 | Editor setup | person + computer | `~/.beon-edit/editor.json` | Claude asks at first use; `doctor` checks the tools |
| 2 | Client profile | client | `skills/client-styles/references/<slug>.md` (public, in the plugin) | Claude asks the first time a client comes up; lessons add to it |
| 3 | Shoot | shoot folder | `<shoot>/_shotlog/shotlog.json`, top-level `shoot` block | Claude reads the footage, asks the gaps, writes it |
| 4 | Job card | edit | `<shoot>/_shotlog/jobs/<concept>.md` + session copy `~/.beon-edit/jobs/<session_id>.md` | the opening grilling |

JSON for anything a hook reads (the hooks run on stock `python3`, no YAML parser).

---

## 1. Editor setup: `~/.beon-edit/editor.json`

Replaces today's `~/.beon-edit/config.json` (its `repo`, `tim_names`, `rules_page` move here).

```json
{
  "name": "Tim",
  "aliases": ["Tim", "Tim Ha"],
  "plugin_owner": true,
  "plugin_repo": "~/code/beon-edit",
  "footage_roots": [
    {"path": "/Volumes/T7 Shield/Raws", "fs": "exfat", "delete_allowed": false}
  ],
  "synced_folders": ["~/Library/CloudStorage/Dropbox"],
  "scratch_root": "~/work",
  "run_env": {"mode": "local"},
  "resolve": {"edition": "studio", "version": "21.1.1", "external_scripting_local": true},
  "tools": {
    "gyroflow": {"installed": true, "stabilize_script": "<Fusion Scripts>/Utility/Gyroflow Stabilize Flagged.py"},
    "footage_prep": {"enabled": true},
    "whisper": {"model": "~/whisper-models/ggml-large-v3.bin"},
    "crisperwhisper": {"python": "~/cw/bin/python", "model_dir": "<path>", "licence": true}
  },
  "rules_page": "<optional link>"
}
```

| Field | Required | Meaning |
|---|---|---|
| `name`, `aliases` | yes | Who this editor is; goes on every job card `Editor:` line and every lesson |
| `plugin_owner` | yes | `true` only for Tim: approved general/client lessons are pushed to `main`. Everyone else: they become a pull request Tim merges or not |
| `plugin_repo` | owner, or anyone sending PRs | Editable clone of the plugin (not the installed cache) |
| `footage_roots[]` | yes | Drives/folders that hold raws; `fs` and `delete_allowed` per root (exFAT `._` files are skipped; deleting is off unless `true`) |
| `synced_folders[]` | yes (may be empty) | Never write media, renders or scratch here (Dropbox, iCloud, Google Drive) |
| `scratch_root` | default `~/work` | Frames, sheets, proxies, DRX/DRT, LUTs; per job `<scratch_root>/<client>-<shoot>/<concept>/` |
| `run_env` | default `{"mode":"local"}` | `local` = plain Mac. `device-vm` (Tim's setup) adds `shell_budget_s`, `mount_map {mac_prefix: vm_prefix}` and the staging folder for sheets |
| `resolve` | yes | Studio 21.1+ only (the free edition has no scripting). `external_scripting_local` = Preferences › System › General › External scripting using: Local |
| `tools.gyroflow` | B-roll jobs | If not installed, B-roll handheld shots can't pass the gate; Claude says so at the grilling |
| `tools.footage_prep` | default `enabled:false` | Off: the fallback (ingest.py + contact sheets) and a one-line notice |
| `tools.whisper`, `tools.crisperwhisper` | optional | Without them: Resolve transcription and energy-based filler checks |
| `rules_page` | optional | Owner only |

`doctor` (to be added: `skills/house-rules/scripts/doctor.py`) checks Resolve, ffmpeg/ffprobe, the Python
packages (numpy, opencv-python-headless, scipy), Gyroflow, fonts the client profiles need (Garet), and
writes nothing; Claude writes editor.json from the editor's answers.

---

## 2. Client profile: `skills/client-styles/references/<slug>.md`

Keeps today's prose sections and provenance tags. Adds a front-matter block with the fixed fields Claude
and the scripts read. `ask` = not known yet: Claude asks at the next grilling and **writes the answer back**.

```yaml
---
slug: arriva
name: Arriva
who: Property developer; Azar presents
people:
  - {name: Azar, role: presenter}
concept_types:
  - {name: testimonial, target_length: "45-60 s"}
footage: {path_pattern: "{root}/Arriva/{Month}/", write_protected: false}
resolve: {project: Arriva, bins: "one bin per month", timeline_naming: "<Month> C<n> v<k>"}
delivery: {aspect: "9:16", resolution: 1080x1920, fps: 24, loudness_lufs: ask, true_peak_db: ask}
end_card: {kind: ask, asset: ask, length_f: ask, music_tail_s: ask}
audio: {dialogue_enhance: ask, music: editor}
subtitles: {look: "<plain words>", title: "Fluid Reveal Words", font: "Garet Book", reference_timeline: ask}
grade: {template_still: "Tim's Color Grading Node Tree #1_1", aroll_policy: per_concept}
language: en
brand_words: ["arriva (lowercase)"]
open_questions: ["Loudness target?"]
---
```

| Field | Required | Meaning |
|---|---|---|
| `slug`, `name`, `who`, `people[]` | yes | The job card `Client:` line holds the slug |
| `concept_types[]` | optional | Usual kinds and lengths; the default for the card's target length |
| `footage` | yes | Where this client's raws live under a footage root; `write_protected` (e.g. Namir on Dropbox) |
| `resolve` | yes | Project name, bin and timeline naming |
| `delivery` | yes | Aspect, resolution, fps, loudness and true peak. Replaces the ~20 places 9:16 1080x1920 24p is hardcoded |
| `end_card` | yes to finish | `kind: file \| compound`, asset path, length, music tail |
| `audio` | yes | Dialogue enhancement tool, who does music |
| `subtitles` | subtitle jobs | The look in plain words + title, font, reference timeline |
| `grade` | grade jobs | Template still override, A-roll policy |
| `language`, `brand_words` | default `en` | Spellings and STT fixes |
| `open_questions[]` | optional | Asked at the next grilling, then removed |

---

## 3. Shoot: `<shoot>/_shotlog/shotlog.json` → `"shoot"`

Already holds client, shoot, days, people, conventions, footage_prep. New keys marked *.

```json
"shoot": {
  "shoot_folder": "/Volumes/T7 Shield/Raws/Arriva/Oct/",
  "client": "arriva", "shoot": "Oct", "location": "…", "days": ["2026-10-14"],
  "cameras": [
    {"folder": "Li's SD CARD", "role": "A", "model": "FX3", "fps": 25, "res": "3840x2160",
     "log": "S-Log3", "gyro": "sony-rtmd", "ext": ".MP4", "name_pattern": "LIAM.A_FX3_*"}
  ],
  "audio": {"mic_camera": "A", "mic_channel": 2, "safety_channel": 1, "safety_offset_db": -6},
  "multicam": {"exists": true, "clip": "Azar Multicam", "audio_ref_camera": "A", "angle_offsets_s": {"B": 11.0}},
  "people": {"Azar": "presenter", "Molly": "stylist"},
  "language": "en",
  "resolve_bin": {"path": "Oct/C1/Shoot", "sorted_bins": []},
  "footage_prep": {"shoot": "Arriva Oct", "available": true},
  "prepped_by": {"editor": "Tim", "machine": "Tim's Mac", "date": "2026-10-15"}
}
```

| Field | Required | Meaning |
|---|---|---|
| `shoot_folder`, `client`, `shoot` | yes | Root of the shoot; parent of `_shotlog/` |
| `cameras[]`* | A-roll / B-roll jobs | Per card folder: role, model, fps, resolution, log profile, gyro source, file extension and name pattern. Probed by Claude, confirmed by the editor. Non-Sony bodies set `gyro: none` |
| `audio`* | A-roll jobs | Which camera and channel carry clean dialogue, and the safety channel |
| `multicam`* | if multi-cam | Multicam clip, audio reference camera, angle offsets |
| `people` | yes for B-roll and supers | The only source of names; Claude never guesses a person |
| `language`* | default from client | Fillers, Whisper |
| `resolve_bin`* | sort / B-roll | Media-pool bin of the shoot |
| `footage_prep` | default `available:false` | Link to the Footage Prep shoot |
| `prepped_by`* | if Footage Prep used | Decision 23: one prepper per shoot; others read, don't re-prep |

---

## 4. Job card: `<shoot>/_shotlog/jobs/<concept>.md`

Kinds: `concept`, `montage` (no dialogue), `footage-sort`, `subtitles-only`, `grade-only`, `fix`.
✔ = the hook blocks Resolve edits until filled on a `concept` job. Write `n/a` when a line doesn't apply.

```markdown
# Job: <client> <concept>
Card: <path to this file>
Kind: concept
Editor: <editor.json name>
Client: <slug>
Shoot: <shoot folder>
Concept: <id, e.g. C1>
Resolve project: <exact name>
Timelines: working <name>; protected <names>; don't count for reuse <names>
Date: <YYYY-MM-DD>
Grilling: done | skipped ("<editor's words>")
Lessons inbox: <shoot>/_shotlog/lessons/<concept>.jsonl

## Answers
- Brief: <link or path> — <one line>
- Concept and goal:
- Target length:
- Story beats / answers to use:
- Speakers: primary <name>; others <names> (drop their backchannels); supers <Name / ROLE>
- Stages: aroll <Claude/editor/none>; broll <…>; grade <…>; subs <…>; music <…>; final <…>
- Delivery: as client | <aspect res fps loudness> (give the resolution when the aspect isn't 9:16; else 1080 on the short side)
- Jokes or light moments: on camera | B-roll allowed
- Goofy or playful people shots: allowed | not
- On-camera holds: <exceptions to the 4 s rule, or n/a>
- Camera / multicam: <angles to cut from>
- Cut style: fillers cut | flag; captions clean | verbatim
- Music: <who>; break planned at <time> | n/a
- Subtitles: <look in plain words>, confirmed by the editor | n/a
- Don't move: <items the editor placed>
- Footage Prep: shoot "<name>" | not available (fallback)
- Run: attended | unattended

## Concept-only notes
- Rules for this concept only (never copied into the plugin).
```

✔ on `concept`: Editor, Client, Shoot, Concept, Resolve project, Timelines (working), Grilling, Brief,
Concept and goal, Target length, Story beats, Speakers, Stages, Delivery. A line counts as unfilled while it is empty, still has a `<placeholder>`,
or still lists the template's choices (`a | b`); write `n/a` when it doesn't apply. On `montage`: the same minus
Story beats and Speakers. Other kinds: Editor, Client, Shoot, Resolve project, Grilling.

---

## 5. Lessons and rule changes

The editor approves their own lessons at the end of the job.

| Lesson kind | Where it goes | Owner (`plugin_owner: true`) | Other editors |
|---|---|---|---|
| concept | job card "Concept-only notes" | saved | saved |
| client | the client profile in the plugin | commit + push to `main` | pull request to the repo |
| general | the skill or reference it changes | commit + push to `main` | pull request to the repo |

A pull request changes nothing until Tim merges it.

---

## 6. Asked only inside a stage (never on the opening card)

- Is the editor in Resolve right now? (stop all Resolve calls; work moves to files)
- Gates: sort plan, beat list, pacing gate, caption look, reusing an A-roll take, grade go-ahead,
  QA creative findings, a 4th QA round.
- Who is this person? (before using someone new for a line)
- The editor's finished timeline name (learn-from-tim).
