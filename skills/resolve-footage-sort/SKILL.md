---
name: "resolve-footage-sort"
description: "This skill should be used when sorting a DaVinci Resolve bin of raw footage into numbered content bins and logging what each clip shows: \"sort this shoot\", \"sort the footage\", \"organise the raws\", \"put the clips into bins\", \"log this shoot\", or step 1 of any edit job. Footage Prep first, then a cheap pixel fingerprint, one look per setup, a gate table for Tim, and renamed copies in numbered bins with the originals kept in an archive bin."
metadata:
  version: "0.3.1"
---

# Resolve footage sort

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). Kind `footage-sort`, or step 1 of an edit job card. No card: stop and run the grilling with Tim. **Footage Prep first** (`house-rules/references/footage-prep.md`). **Shot log first** (shotlog). Nothing changes in Resolve before Tim approves the gate table.

## 0. What it does

Two outputs:
1. Numbered bins inside the shoot bin, holding renamed copies of every usable clip. The shoot bin itself is the archive: the originals stay at its root with their original names.
2. Per-clip content in `<shoot>/_shotlog/shotlog.json`, so later skills can cite a reason (`C0123 place=bakery scene=bakery-2 setup=bakery-2-s01 tag=names_place:bakery fp=hero stab 0.93`).

Who owns what:
- **Footage Prep** owns technical quality: tier, flags, movement, stability, selects. Claude never re-measures shake and never copies technical state into its own fields. Scripts read it live.
- **Claude** owns content: place, subject, concept, scene, setup, what the clip shows, roles, good_for, not_for.
- **Tim** owns the final bins. His moves and renames always win.

Long tables (families, vocabularies, good_for grammar) live in `references/taxonomy.md`. The sort never transcribes. Interviews are aroll-cut's job.

## 1. Sort axis (ask per shoot)

Never assume place first. After the cheap look, propose the axis that fits most of the footage and how it was shot:
- **place**: walkthroughs, suburbs, venues. Bins by room or landmark.
- **subject**: one person, product or location runs through the whole shoot. Bins by what the subject is doing, or by setup.
- **concept**: a montage of a theme, like objects or textures. Bins by motif.

Pick by majority of setups. Tim confirms or changes it at the gate. The shot log keeps place, subject and concept fields either way. Only the bins change.

## 2. Three levels, always kept apart

| Level | What it is | Example id | Used for |
|---|---|---|---|
| `place` | where, at bin level on a place sort | `bakery` | bins, line matching, "3 in a row" rule |
| `scene` | one place, one light, one session | `bakery-1` | "same scene" rule, grade groups |
| `setup` | one camera position, near-identical frames | `bakery-1-s03` | "different angle" rule, retakes |

A scene is always place-based. Subject and concept are their own fields. A flower shot by the bakery is `place=bakery`, `subject=nature`, binned in Details with `place.inferred: true`.

## 3. Pipeline

All output goes to a scratch dir outside Dropbox. The scripts refuse any path with `Dropbox` or `_shotlog` in it, symlinks resolved. Run each with `--help` for the full flags. The file contracts are in section 9.

### Step 1. Scope (pop-up question tool)
Ask once: project, shoot bin path (`<Month>/<Job>/<Shoot>`), Footage Prep shoot, anything Tim already sorted (never re-sort it), and whether Resolve is free. Write the job card.

### Step 2. Footage Prep (read-only tools)
`library_shoots`, `shoot_summary`, then `clips` (page past 200) and `selects` saved to files in scratch. `clip_detail` only where needed. Never paste the lists into context. Never pass `switch_shoot`. Never call rate, undo, apply_preset, cancel_job, send_to_resolve or import.

### Step 3. `scripts/sort_inventory.py` writes `manifest.json`
One quick external read of the shoot bin (the `_resolve.py` connect pattern, not run_script). It refuses if the open project is not the expected one. It joins Resolve and Footage Prep by the clip's `fp.clip` metadata or by File Path ending in the FP relative path. Never by clip name. ffprobe reads each file, but never an online-only one. It sets per clip:
- **state:** `settled` (its copy sits in the bin `sort_copy.bin` names, or it is an approved archive-only clip at the current `sort.v`), `moved_by_tim` (Tim moved or deleted the copy: Tim wins, log it in `sort.tim`), `missing` (report only), `new`. Only `new` clips go on. A clip from "Only write the shot log" (`sort.approved: false`) is `new` again. Reuse its shot log content instead of a new look.
- **role** by rule: `aroll` (60 s or more, locked or steady, speech-like audio), `multicam_angle`, `audio`, `junk_candidate` (under 1.5 s, dark and silent, or reject with no selects), `broll`.
- **excluded:** timelines, multicam and compound clips, Gyroflow renders, proxies, subclips, Selects bins. Listed, never touched.
- **mismatches:** in Resolve not in FP, in FP not in Resolve.

Tier is Tim's tier when set, else auto_tier. If nothing is `new`, say "nothing to sort" and stop.

### Step 4. `scripts/sort_group.py` writes `groups.json`
- **Sessions:** an idle gap over 300 s starts one. A hint of a new place or light, never proof.
- **Setups:** a blurred 32x18 gray fingerprint at the middle of the best clean select, compared with the last 3 clips in the session. The closest one counts. d under 0.35 within 90 s joins that setup as a member. 0.35 to 0.8 starts a setup with band `maybe` and `maybe_of` (Claude merges or keeps it on the sheet). Over 0.8 is band `new`. FP `duplicate_of` joins too. Leader = highest FP best_score. Retakes stay together.
- **The fingerprint only catches true retakes.** A reframed shot of the same thing scores like a different shot of the same street, so expect most setups to hold one clip and about 1 in 7 to be `maybe`. Claude does the real merging on the sheet.
- **Sheets:** one 320 px frame per setup leader, 5x5 tiles, strict manifest order, a black cell at each session break, a `map_file` per sheet.
- **Strips:** 3 frames (select in, mid, out) for pans, tilts, gimbal moves, handheld with more than one movement chip (FP chips other than shaky) and clips over 30 s. Up to 8 per strip sheet.
- Online-only and missing files are skipped and listed in `errors`. A rerun clears the old sheets first.

### Step 5. Claude reads the sheets, writes `looks.json`
Read every sheet once with its map. One entry per setup: place, subject, concept, shot_size, angle, light, people_detail, content, roles, good_for, not_for, vertical, subject_x, confidence. A clip that differs from its setup (a tighter take) goes in `overrides`.

Second look (one 960 px frame or a 640 px strip), about 10% of setups: low confidence, a bin that ends up with 1 or 2 clips, sign text or a brand that decides a not_for, a person a concept will need. Describe people by clothing and action. Never name them unless the people registry or Tim does. Still unsure: listed, no copy, stays only in the archive.

### Step 6. Claude writes `plan.json`
Derive scenes (same place, same session, no light change), pick the axis, then bins by section 4. Enforce the size rules on the real result. `bins[]` holds names and parent, `copies[]` holds key, uid, target bin and the new clip name, `shotlog_updates` holds the sort fields per key.
- Every clip with an update gets either a copy or `sort.archive_only: true` (rejects and unsure clips). Never both.
- `sort_role` is the manifest's rule role. `roles` is the taxonomy content list.
- Never put `bin` or `sort_copy` in `shotlog_updates`. sort_apply writes them only after a verified copy.

### Step 7. Gate (pop-up question tool)
Table: bin | clips | clip ranges | B-roll ready | hero moments | what is in it. B-roll ready = clips with a hero clean select at stability 0.75 or more, read live.

Below it: the proposed axis and the other two in one line each, judgement calls, unsure clips, rejects (archive only), thin bins (B-roll ready under 3), not_for warnings (brand, political, minors, recognisable strangers), excluded items, mismatches, and the archive rename if any.

Options: Approve / I'll change some / Only write the shot log (`sort_apply.py plan.json --shotlog-only --shotlog <log> --apply`, no Resolve calls) / Stop. Tim's changes come back as plain lines ("0123 to Details", "rename 05 to Park"). Update `plan.json`, record them in `sort.tim`, show the table again only if bins changed.

### Step 8. `scripts/sort_apply.py`, a dry run first
- `sort_apply.py plan.json --shotlog <shoot>/_shotlog/shotlog.json` is a dry run (the default, `--dry-run` says it out loud). It checks the plan and the shot log first, then prints the bins to create, the copies per bin and the names. Check the printout.
- Then the same with `--apply`, only when Resolve is free. See section 5.
- Other flags: `--shotlog-only` (gate answer "Only write the shot log"), `--test-bin _claude_sort_test` with `--limit N` and `--cleanup-test` (tests only).

### Step 9. Shot log and report
sort_apply re-reads `shotlog.json` right before writing and merges. It never touches `footage_prep` keys. Content fields can go in before approval with `--shotlog-only` (`sort.approved: false`). `bin` and `sort_copy` are written only after a verified copy. Save the plan to `_shotlog/plans/sort-<YYYY-MM-DD>.json` (text only). sort_apply writes `shotlog.json` in Footage Prep's own format and regenerates `shotlog.csv` with the same bytes the app writes.

Report: bin, count, what is in it. Then unsure clips, rejects, thin bins, not_for warnings, mismatches, excluded items, the scratch path (Tim clears it), time taken and images read. Plain short sentences.

## 4. Bins

### Tree and naming
```
<Month>/<Job>/<Shoot>              the shoot bin IS the archive: every original and reject at its root
    01 A-roll                      interviews, pieces to camera, multicam (only if present)
    NN <Name> <Activity> - People  a named subject from the people registry only
    NN <axis bins>                 journey order on a place sort, shoot order on subject or concept
    NN Details                     one bin: close-ups, nature, texture that could be anywhere
    NN Audio                       wav, music, room tone (only if present)
```
- The numbered bins sit inside the shoot bin. There is no separate archive bin.
- Renaming the shoot bin to `00 Archive - All Footage` is optional and only if Tim says yes. The API has no bin rename, so Tim does it by hand after the run. Then pass the new name as `--bin` next time. `sort_copy.bin` is relative to the shoot bin, so the rerun state survives. The full `bin` paths in the shot log go stale until the next sort_apply run.
- Two digits, consecutive, no gaps. Leave out what is not there.
- `NN Name`, Title Case, "and" never "&", at most 3 nouns, at most 32 characters. Plain words a script line would say (`03 Bakery`, `05 Park`), never a category like "Landmarks and Heritage".
- Never a client, agent or brand name in a bin. Never tiers or scores. Street names only for signboard shoots.
- On reruns never renumber. New bins take the next free number.

### Size
- At least 3 clips per bin, else merge into the nearest bin of the same family, or the nearest by session.
- At most about 10 axis bins.
- Split a bin over 25 clips only when it holds two things a script could name separately.

### Families
Families per shoot kind (property, suburb, event, office, signboards, interview, aerial) and the subject and concept bin patterns are in `references/taxonomy.md`. A new family is proposed to Tim and added only after he approves.

### Edge rules
- **Place comes back later:** one bin, two scenes (`bakery-1`, `bakery-2`).
- **Clip crossing two places:** bin by where its best select lies. Record `places_in_clip`.
- **Passers-by:** stay in their place bin. Only a registry person as subject gets a People bin. At events where guests are the content, Guests and Mingling is a place bin.
- **Rejects:** archive only, no copy. They still get a content line so Tim can rescue one. A place with only a reject is listed as thin at the gate.
- **Retakes:** never left out for being a retake. The whole take family is copied.
- **Usable or hero with flags:** copied as normal. B-roll filters on FP flags later.
- **Per-card clients:** follow the client profile `sort_mode`. Ask once if it is not set.
- **Already sorted bins:** reuse them. Never touch a bin Tim made.

## 5. Archive method B (copies)

- The originals never move and never get renamed. Rejects live only in the archive.
- Each non-reject, non-unsure clip gets a second pool clip: the same file imported into its numbered bin. Resolve makes it a separate clip with a new MediaId. The original is untouched.
- The copy's Clip Name is descriptive and always ends in the camera clip number: `Bakery front wide C0123`.
- Footage Prep markers (color, name, note, duration, customData) and keywords are copied over. Sort keywords are appended, never replaced: `place:<id>`, `subject:<id>`, `concept:<id>` (when set) and the primary role as `role:<role>` (`role:establishing`), so a role never reads like a bare copy of `place:<id>`.
- Every copy gets `beon.sort_copy = 1` and `beon.sort_src = <original UniqueId>` as third-party metadata.
- Reruns skip copies already in the target bin (same File Path plus `beon.sort_copy`), so a half-finished run resumes.

### Resolve rules
- External python only, through the `_resolve.py` connect pattern. Refuse if the open project is not the job card project.
- Never switch projects or timelines. Never CreateEmptyTimeline or SetSetting. Never set clip colour Orange (it triggers Stabilize Flagged).
- Create bins one at a time, then read the subfolders back.
- `SetClipProperty("Clip Name", ...)` returns False even when it works. Read the name back and trust that.
- `DeleteFolders` resets the current folder. Always restore it. Restore Tim's current folder at the end of every run.
- Keep calls few and quick. Stop all Resolve calls, reads included, when Tim says he needs Resolve. The shot log keeps going.
- After the copies, one check: every planned copy is there once with the right name, marker count and `beon.sort_src`, and the originals are unchanged. Problems are reported. Rerun to retry: it resumes and only does what is missing.

### Known gap: Footage Prep Send
Send indexes the pool by File Path and keeps the first clip it meets. With two clips per file it can tag or cut from either one. Until the app prefers one side by `beon.sort_copy`, run Send before the sort, or re-run sort_apply after a Send to top up the markers on the copies.

## 6. Cost
- Frames: about 0.2 s per setup locally.
- Images read: ceil(setup cells / 25) sheets, plus ceil(strips / 8) strip sheets, plus about 10% second looks. On a 75 clip suburb shoot: 3 sheets, 4 strip sheets, about 7 second looks.
- Resolve: one inventory read, then one apply run per gate approval.

## 7. Fallback
Footage Prep unreachable or not analysed: tell Tim in one line and carry on. Take tiers and shake from `shotlog/scripts/ingest.py`, set `footage_prep.available: false`, use clip middles as keyframes and strips for every clip over 6 s. Everything else stays the same. Rejects then come from Claude's look, so list each one at the gate.

## 8. Public repo hygiene
The skill and scripts carry generic examples only. No client names, people, addresses, paths or frames. Per-shoot data lives only in `<shoot>/_shotlog/` and scratch.

## 9. File contracts (scratch dir)

- `manifest.json`: `{shoot_bin, project, generated_at, sort_v, clips:[{key (File Path), name, uid, folder, duration_s, fps, recorded_at, camera, fp:{clip_path, tier, auto_tier, movement, chips, stability, best_score, flags, selects:[{in_s, out_s, score, stability}], duplicate_of}, state, now_in, copies, probe_error, role, excluded_reason}], excluded:[{name, reason}], mismatches:{in_resolve_not_fp, in_fp_not_resolve}}`.
- `groups.json`: `{sessions:[{id, clip_keys}], setups:[{id, session, leader_key, member_keys, keyframe_s, d_prev, band (new|maybe), maybe_of}], sheets:[{file, map_file}], strips:[{clip_key, file}], clip_setup, errors}`. Same-setup clips are members, so band is never `same`.
- `looks.json` (Claude): `{setups:{<setup id>:{place, subject, concept, shot_size, angle, light, people_detail, content, roles, good_for, not_for, vertical, subject_x, confidence}}, overrides:{<key>:{...}}}`.
- `plan.json` (Claude, after the gate): `{project, shoot_bin, axis, archive:{rename_to}, bins:[{name, parent}], copies:[{key, uid, bin, clip_name}], shotlog_updates:{<key>:{...sort fields, sort:{archive_only}}}}`.
