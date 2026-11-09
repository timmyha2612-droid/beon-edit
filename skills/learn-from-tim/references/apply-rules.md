# Writing approved lessons into the plugin

Only lessons Tim approved or changed (`lessons.py list <inbox> --status approved` / `--status changed`).
Never anything `open`, `pending-tim`, `dropped` or `concept`.

## Find the plugin clone

The installed plugin is a cached copy; the rules live in the git clone it was installed from.
1. `~/.beon-edit/config.json` `{"repo": "/path/to/beon-edit"}` if it exists; else `~/code/beon-edit` (README setup).
2. Check it: `git -C <repo> remote get-url origin` ends in `beon-edit(.git)`, and `git -C <repo> status --short`
   is clean. Not found or dirty: stop and ask Tim where the clone is (then write the config file).
3. It must be on main with a clean tree: `git -C <repo> rev-parse --abbrev-ref HEAD` is `main` (else
   `git -C <repo> checkout main` when clean; otherwise ask Tim). Then `git -C <repo> pull --ff-only`.

## Tim is the editor

1. For each approved lesson, make exactly the change stored in its proposal (`file`, `section`, `change`,
   `old_line`, `new_line`; Tim's `change` wording replaces the line). Nothing that isn't in an approved proposal. One line per rule, the plugin's
   plain style, tagged `[Tim, <concept>, <date>]` (what he said) or `[inferred, <concept>]` (measured, and Tim
   agreed it as a default). `replace`: change the old line, don't leave both. Client lessons go in the client
   profile (copy `_template.md` if the client has none, and add it to the client-styles Profiles table).
2. Promotion to a general rule (Q17): only as an approved lesson with `promote_from`. Add the general line and
   remove exactly the `remove_lines` it lists from the client profiles (Tim saw them in the table).
3. Bump the patch version in `.claude-plugin/plugin.json` (0.18.0 -> 0.18.1) and the touched skill's
   `metadata.version`.
4. Add a changelog line to README: `<version> (<date>, learned from <concept>): <one line per rule>`.
5. Show Tim the diff (`git -C <repo> diff`) in one short message, then `git -C <repo> pull --ff-only` again,
   commit, and `git -C <repo> push origin main`. Tim's yes on the lessons is the go-ahead (Q15). Commit message:
   `Learn from <concept>: <short summary>`. Push rejected: `pull --rebase`, re-check the diff (version numbers
   may collide: take the next free patch number), push again; never force-push.
6. Only after the push succeeded (`git -C <repo> status -sb` shows no ahead count):
   `lessons.py applied <inbox> <id> --file <path> --commit <sha>` for each lesson.
7. Tell Tim to refresh the plugin (`/plugin marketplace update beon`, or it updates on the next start).
8. If the "Tim's Edit System" page is set up (`rules_page` in the config), update it from the plugin so it shows
   the new rules, and clear the marks that were applied.

## Not Tim (another editor)

Only Tim turns lessons into rules (Q1). The editor's decisions are stored as `pending-tim`.
- With push access to the repo: make a branch `lessons/<editor>-<concept>-<date>` from main, make the same edits
  as above for the lessons the editor approved or changed (leave out the ones they dropped, and list those
  separately in the PR so Tim can overrule), push it, and open a pull request for Tim listing each lesson (who said it, the evidence). Tim merging
  it is his yes; then record `decide ... --by Tim` and mark them applied.
- Without push access: write `<shoot>/_shotlog/lessons/pending-for-tim.md` with the `lessons.py propose` table
  and the learner's proposed lines, and tell the editor to let Tim know.
