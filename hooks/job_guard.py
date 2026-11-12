#!/usr/bin/env python3
"""PreToolUse guard for DaVinci Resolve tools (beon-edit plugin): no Resolve edits before the intake.

Rule since 9 Nov 2026: every job starts with the opening questions, because every concept is different.
The editor running the job answers them, and the answers go into a job card
(house-rules/references/intake.md section 4). This hook blocks any Resolve call that CHANGES the project until
  1. this person/computer has an editor setup at ~/.beon-edit/editor.json (intake.md section 1), and
  2. this session has a job card copy at ~/.beon-edit/jobs/<session_id>.md whose Kind is known and whose
     required lines for that Kind are filled (beon_config.missing_lines).
Reads (get/list/export, probes, dry runs, read-only scripts) always pass, so learn-from-tim and looking
around stay free.

Limits: it only sees Resolve MCP calls. Python run from Bash (gyroflow_headless.py, broll_gate.py)
isn't checked; those run after the grilling anyway.
If beon_config can't be imported it falls back to the old check (card exists + Grilling line) and says so.
Exit 2 = block; the message goes back to Claude."""
import json, os, pathlib, re, sys

try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "house-rules" / "scripts"))
    import beon_config as bc
except Exception as e:                       # fail open on the new checks, keep the old card check
    bc = None
    sys.stderr.write(f"beon-edit job gate: can't import beon_config ({e}); checking only that a job card exists.\n")

if bc:
    JOBS = str(bc.JOBS)
    HOME = str(bc.HOME)
else:
    HOME = os.path.expanduser(os.environ.get("BEON_HOME", "~/.beon-edit"))
    JOBS = os.path.expanduser(os.environ.get("BEON_JOBS_DIR", os.path.join(HOME, "jobs")))

# Resolve API calls that change the project (run_script bodies)
WRITE_CALLS = re.compile(r"""\b(AppendToTimeline|InsertFusionTitleIntoTimeline|InsertGeneratorIntoTimeline|
    InsertTitleIntoTimeline|InsertFusionCompositionIntoTimeline|InsertOFXGeneratorIntoTimeline|
    CreateTimelineFromClips|CreateEmptyTimeline|DuplicateTimeline|DeleteTimelines|ImportTimelineFromFile|
    DeleteClips|DeleteMarker\w*|AddMarker|SetProperty|SetSpeed|SetClipColor|ClearClipColor|SetName|
    SetClipEnabled|SetTrackEnable|SetTrackName|AddTrack|DeleteTrack|AddTransition|SetLUT|SetCDL|
    ApplyGradeFromDRX|CopyGrades|ResetAllGrades|CreateMulticamClip|CreateCompoundClip|MoveClips|MoveFolders|
    AddSubFolder|DeleteFolders|ImportMedia|RelinkClips|UnlinkClips|SetClipProperty|SetMetadata|
    AddRenderJob|DeleteRenderJob|DeleteAllRenderJobs|StartRendering|SetRenderSettings|LoadRenderPreset|
    SaveAsNewRenderPreset|DeleteRenderPreset|SetSetting|Stabilize|SmartReframe|CreateSubtitlesFromAudio|
    TranscribeAudio|ClearTranscription|SetCurrentRenderFormatAndCodec|AddFusionComp|ImportFusionComp|
    LoadFusionCompByName|DeleteFusionCompByName|SetInput|AddVersion|LoadVersionByName|DeleteVersionByName|
    UpdateMarkerCustomData|SetStart|SetEnd|SetLeftOffset|SetRightOffset)\s*\(""", re.X)

# MCP tool names / action arguments that change the project (incl. the action-style davinci-resolve
# tools: timeline, timeline_item, media_pool, render, ... take {"action": "...", "params": {...}})
WRITE_VERBS = re.compile(r"(^|[_\s.-])(add|create|delete|remove|move|set|apply|append|insert|import|update|"
                         r"rename|replace|relink|unlink|link|clear|stabilize|render|duplicate|reset|copy|"
                         r"transcribe|enable|disable|trim|split|paste|lift|overwrite|flatten|modify|normalize|"
                         r"align|sync|organize|load|save|start|stop|quit|convert|setup|capture|assemble|"
                         r"restore|bulk|ripple)([_\s.-]|$)", re.I)
# switching what's shown (timeline, page, playhead, selection, UI state) changes nothing in the edit
NAVIGATION = re.compile(r"set[_\s.-]?(current|playhead|timecode|page|open[_\s.-]?page|selected)|open[_\s.-]?page|"
                        r"goto|go[_\s.-]to|(save|restore)[_\s.-]state", re.I)

# reads, whatever verb comes later in the name (get_start_frame, list_jobs, probe_render_settings)
READS = re.compile(r"^(get|list|probe|is|has|check|validate|inspect|search|describe|verify|detect|propose|"
                   r"export|api|job|runtime|verification|story|clip[_\s.-]where|thumbnail|marker[_\s.-]thumbnail|"
                   r"source[_\s.-]range|action[_\s.-]help)([_\s.-]|$)", re.I)


def _params(tin):
    p = tin.get("params")
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except ValueError:
            p = {}
    return p if isinstance(p, dict) else {}


def is_write(tool, tin):
    params = _params(tin)
    script = tin.get("script") or tin.get("code") or params.get("script") or params.get("code") or ""
    if script:
        return bool(WRITE_CALLS.search(str(script)))
    if params.get("dry_run") is True or tin.get("dry_run") is True:
        return False                                   # a dry run changes nothing
    actions = [str(v) for k, v in tin.items() if k in ("action", "method", "operation", "command", "op")]
    # an action-style tool is judged by its action (render/list_jobs is a read); others by the tool name
    for name in actions or [tool.split("__")[-1]]:
        if READS.search(name) or NAVIGATION.search(name):
            continue
        if WRITE_VERBS.search(name):
            return True
    return False


SETUP_HELP = ("Run the editor setup from house-rules (references/intake.md section 1): Claude asks the editor "
              "the questions and writes {path}. It is created once per person and computer, not per job.")
CARD_HELP = ("Every job starts with the opening grilling (house-rules), because every concept is different. "
             "Read the client profile, ask the editor the open questions with the pop-up question tool, write the "
             "job card (house-rules/references/intake.md section 4) into <shoot>/_shotlog/jobs/, then copy it to:\n"
             "  {path}\n"
             "If the editor said to skip the questions, write 'Grilling: skipped (\"<their words>\")'; the required "
             "lines for the Kind still apply (intake.md section 4): fill what you know, write n/a for a line that "
             "doesn't apply.")
FIX_HELP = ("The card exists, so don't run the full grilling again (house-rules/references/job-card.md "
            "'Resuming' and 'Old cards'). Read the real card (its 'Card:' line), ask the editor with the pop-up "
            "question tool whether anything changed and to confirm the missing lines, then add only those lines "
            "(n/a where one doesn't apply) to the real card and to the session copy:\n"
            "  {path}")


def card_problem_old(text):
    """Fallback when beon_config can't be imported: only the Grilling line."""
    if not re.search(r"^Grilling:\s*\S", text, re.M):
        return "the card has no 'Grilling:' line (done with the editor, or skipped with their words)"
    return None


def card_problem(text):
    card = bc.parse_card(text)
    kind_raw = card.get("Kind") or ""
    kind = kind_raw.split("|")[0].strip().lower()
    problems = []
    if bc.unfilled(kind_raw) or kind not in bc.KINDS:
        problems.append(f"'Kind:' must be one of {', '.join(bc.KINDS)} (it is {kind_raw or 'missing'!r})")
    need = bc.missing_lines(card)          # a skipped grilling still needs the Kind's lines (intake.md section 4)
    if need:
        problems.append("these card lines are missing or still a placeholder: " + ", ".join(need))
    return "; ".join(problems) or None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name") or ""
    tin = data.get("tool_input") or {}
    if not isinstance(tin, dict) or not is_write(tool, tin):
        sys.exit(0)
    sid = data.get("session_id") or "unknown"
    path = os.path.join(JOBS, f"{sid}.md")
    editor_json = os.path.join(HOME, "editor.json")
    if bc and not os.path.exists(editor_json):
        sys.stderr.write(
            "beon-edit job gate: Resolve edits are blocked because this computer has no editor setup "
            f"({editor_json} is missing).\n" + SETUP_HELP.format(path=editor_json) + "\n"
            "Reading Resolve (get/list/export, probes, read-only scripts) is not blocked.\n")
        sys.exit(2)
    problem = None
    card_exists = os.path.exists(path)
    if not card_exists:
        problem = "no job card is linked to this session"
    else:
        try:
            text = open(path, encoding="utf-8").read()
            problem = card_problem(text) if bc else card_problem_old(text)
        except Exception as e:
            problem = f"can't read the job card ({e})"
    if not problem:
        sys.exit(0)
    sys.stderr.write(
        f"beon-edit job gate: Resolve edits are blocked because {problem}.\n"
        + (FIX_HELP if card_exists else CARD_HELP).format(path=path) + "\n"
        "Reading Resolve (get/list/export, probes, read-only scripts) is not blocked.\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
