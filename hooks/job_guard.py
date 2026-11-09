#!/usr/bin/env python3
"""PreToolUse guard for DaVinci Resolve tools (beon-edit plugin): no Resolve edits before the grilling.

Tim's rule (9 Nov 2026): every job starts by asking him the opening questions, because every concept
is different. The answers go into a job card (house-rules/references/job-card.md). This hook blocks
any Resolve call that CHANGES the project until this session has a job card linked at
~/.beon-edit/jobs/<session_id>.md. Reads (get/list/export, read-only scripts) always pass, so
learn-from-tim and looking around stay free.

Limits: it only sees Resolve MCP calls. Python run from Bash (gyroflow_headless.py, broll_gate.py)
isn't checked; those run after the grilling anyway.
Exit 2 = block; the message goes back to Claude."""
import json, os, re, sys

JOBS = os.path.expanduser(os.environ.get("BEON_JOBS_DIR", "~/.beon-edit/jobs"))

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

# MCP tool names / action arguments that change the project
WRITE_VERBS = re.compile(r"(^|[_\s.-])(add|create|delete|remove|move|set|apply|append|insert|import|update|"
                         r"rename|replace|relink|unlink|link|clear|stabilize|render|duplicate|reset|copy|"
                         r"transcribe|enable|disable|trim|split|paste)([_\s.-]|$)", re.I)
# switching what's shown (timeline, page, playhead) changes nothing in the edit
NAVIGATION = re.compile(r"set[_\s.-]?(current|playhead|timecode|page|open[_\s.-]?page)|open[_\s.-]?page|goto|go[_\s.-]to", re.I)


def is_write(tool, tin):
    script = tin.get("script") or tin.get("code") or ""
    if script:
        return bool(WRITE_CALLS.search(script))
    short = tool.split("__")[-1]
    actions = [str(v) for k, v in tin.items() if k in ("action", "method", "operation", "command", "op")]
    for name in actions + [short]:
        if NAVIGATION.search(name):
            continue
        if WRITE_VERBS.search(name):
            return True
    return False


def card_problem(text):
    if not re.search(r"^Grilling:\s*\S", text, re.M):
        return "the card has no 'Grilling:' line (done with Tim, or skipped with Tim's words)"
    if re.search(r"^Grilling:\s*skipped", text, re.M | re.I):
        return None
    kind = re.search(r"^Kind:\s*(\S+)", text, re.M)
    if kind and kind.group(1).lower().startswith("concept"):
        for field in ("Concept and goal", "Target length"):
            m = re.search(rf"^- {field}:[ \t]*(.*)$", text, re.M)
            if not m or not m.group(1).strip():
                return f"'{field}' is empty"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name") or ""
    tin = data.get("tool_input") or {}
    if not is_write(tool, tin):
        sys.exit(0)
    sid = data.get("session_id") or "unknown"
    path = os.path.join(JOBS, f"{sid}.md")
    problem = None
    if not os.path.exists(path):
        problem = "no job card is linked to this session"
    else:
        try:
            problem = card_problem(open(path, encoding="utf-8").read())
        except Exception as e:
            problem = f"can't read the job card ({e})"
    if not problem:
        sys.exit(0)
    sys.stderr.write(
        f"beon-edit job gate: Resolve edits are blocked because {problem}.\n"
        "Tim's rule: every job starts with the opening grilling (house-rules), because every concept is different. "
        "Read the client profile, ask Tim the open questions with the pop-up question tool, write the job card "
        "(house-rules/references/job-card.md) into <shoot>/_shotlog/jobs/, then copy it to:\n"
        f"  {path}\n"
        "If Tim said to skip the questions, write a card with 'Grilling: skipped (Tim said \"...\")'. "
        "Reading Resolve (get/list/export, read-only scripts) is not blocked.\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
