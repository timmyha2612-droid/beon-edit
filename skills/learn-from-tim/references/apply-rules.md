# Writing approved lessons into the plugin

Only lessons the editor running the job approved or changed (`lessons.py list <inbox> --status approved` /
`--status changed`). Never anything `open`, `pending-approval` (old inboxes: `pending-tim`), `dropped` or `concept`.
`lessons.py ship <inbox>` prints the commands below filled in for this editor and job; it runs nothing.

Who does what (`~/.beon-edit/editor.json`):
- `plugin_owner: true` (Tim): commit and push to `main`.
- Everyone else: a branch and a pull request. It changes nothing until Tim merges it. Never push to `main`.

## Find the plugin clone

The installed plugin is a cached copy; the rules live in the git clone it was installed from.
1. `editor.json` `plugin_repo` (an old `~/.beon-edit/config.json` `repo` still counts); else `~/code/beon-edit`.
2. Check it: `git -C <repo> remote get-url origin` ends in `beon-edit(.git)`, and `git -C <repo> status --short`
   is clean. Not found or dirty: stop and ask the editor where the clone is (then write `plugin_repo`).
   An editor without a clone: `gh repo clone <origin of the installed plugin> ~/code/beon-edit` and set `plugin_repo`.
3. It must be on main with a clean tree: `git -C <repo> rev-parse --abbrev-ref HEAD` is `main` (else
   `git -C <repo> checkout main` when clean; otherwise ask the editor). Then `git -C <repo> pull --ff-only`.

## Making the edits (both routes)

1. For each approved lesson, make exactly the change stored in its proposal (`file`, `section`, `change`,
   `old_line`, `new_line`; the editor's `change` wording replaces the line). Nothing that isn't in an approved
   proposal. One line per rule, the plugin's plain style, tagged `[<editor>, <concept>, <date>]` (what they said)
   or `[inferred, <concept>]` (measured, and the editor agreed it as a default). `replace`: change the old line,
   don't leave both. Client lessons go in the client profile (copy `_template.md` if the client has none, and add
   it to the client-styles Profiles table).
2. Promotion to a general rule (Q17): only as an approved lesson with `promote_from`. Add the general line and
   remove exactly the `remove_lines` it lists from the client profiles (the editor saw them in the table).

## Plugin owner

3. Bump the patch version in `.claude-plugin/plugin.json` (0.18.0 -> 0.18.1) and the touched skill's
   `metadata.version`.
4. Add a changelog line to README: `<version> (<date>, learned from <concept>): <one line per rule>`.
5. Show the owner the diff (`git -C <repo> diff`) in one short message, then `git -C <repo> pull --ff-only` again,
   commit, and `git -C <repo> push origin main`. The owner's yes on the lessons is the go-ahead (Q15). Commit
   message: `Learn from <concept>: <short summary>`. Push rejected: `pull --rebase`, re-check the diff (version
   numbers may collide: take the next free patch number), push again; never force-push.
6. Only after the push succeeded (`git -C <repo> status -sb` shows no ahead count):
   `lessons.py applied <inbox> <id> --file <path> --commit <sha>` for each lesson.
7. Tell the owner to refresh the plugin (`/plugin marketplace update beon`, or it updates on the next start).
8. If `rules_page` is set in `editor.json`, update that page from the plugin so it shows the new rules, and clear
   the marks that were applied. `rules_page` unset: skip this step.

## Other editors

Same edits (steps 1-2), but no version bump and no changelog line: the owner does those when merging.
Leave out the lessons the editor dropped, and list them in the pull request so the owner can overrule.

```sh
B=lessons/<editor>-<concept>-<date>          # e.g. lessons/jo-smith-c9-2026-11-12 (lowercase, dashes)
git -C <repo> fetch origin
git -C <repo> switch -c "$B" origin/main
# ... make the edits ...
git -C <repo> diff                            # show the editor
git -C <repo> add -A
git -C <repo> commit -m "Learn from <concept>: <short summary>"
git -C <repo> push -u origin "$B"
(cd <repo> && gh pr create --base main --head "$B" --title "Learn from <concept>: <short summary>" --body-file <body.md>)
git -C <repo> switch main
```

- PR body: `lessons.py ship <inbox>` writes it to `<inbox dir>/<concept>-pr.md`, or to `--body-out <body.md>` (each lesson: rule, kind, file, who said it,
  the evidence; then the dropped ones).
- Push refused (no write access to the repo): fork once and push the branch there:
  `(cd <repo> && gh repo fork --remote --remote-name fork)`, `git -C <repo> push -u fork "$B"`, then
  `gh pr create --base main --head <github-user>:"$B" ...`.
- `gh` not installed or not logged in (`gh auth status`): don't push anything. Write
  `<shoot>/_shotlog/lessons/pending-for-tim.md` with the body and the `git -C <repo> diff`, and tell the editor
  to send it to Tim.
- Record each lesson: `lessons.py applied <inbox> <id> --file <path> --pr <url>` (status `in-pr`). When Tim has
  merged it, `lessons.py applied <inbox> <id> --file <path> --commit <merge sha>`. If he closes it unmerged, the
  plugin stays as it was; note it on the job card and close the lesson so the inbox stops showing it as open:
  `lessons.py decide <inbox> <id> drop --by "<editor>" --note "PR closed: <url>"` (or `lessons.py revise ...` to
  propose it again).
- Tell the editor the pull request link. The rules apply to their next jobs only after the merge and a plugin
  refresh.
