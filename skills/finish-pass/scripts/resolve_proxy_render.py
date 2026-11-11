"""Render a small proxy of the current timeline for render_check.py, leaving Tim's render settings as they were.
Run through the Resolve MCP run_script_unsafe tool (it writes a file), only while Tim isn't using Resolve.
Three short calls, because a render outlasts the 60 s script limit:
  STEP = "start"    save Tim's current render settings as a temporary preset, set a 540x960 H.264
                    proxy (single clip, video + audio) into OUT_DIR, add the job and start it
  STEP = "poll"     report progress (call again until done)
  STEP = "restore"  delete the proxy job, load Tim's settings back from the temporary preset and
                    delete that preset
OUT_DIR must be set per shoot (e.g. <shoot folder>/_claude_scratch/proxy) and must be outside Dropbox."""
OUT_DIR = ""  # set per shoot before running, e.g. "/Volumes/T7 Shield/Raws/<Client>/<Month>/_claude_scratch/proxy"
NAME = "proxy_check"
STEP = "start"
KEEP = "zz_claude_restore_render_settings"

if not OUT_DIR or "dropbox" in OUT_DIR.lower():
    raise SystemExit("resolve_proxy_render: set OUT_DIR to the shoot's _claude_scratch/proxy folder (not Dropbox)")
proj = resolve.GetProjectManager().GetCurrentProject()
out = {}
if STEP == "start":
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    if KEEP in (proj.GetRenderPresetList() or []):
        proj.DeleteRenderPreset(KEEP)
    out["saved"] = proj.SaveAsNewRenderPreset(KEEP)
    out["was"] = proj.GetCurrentRenderFormatAndCodec()
    proj.SetCurrentRenderMode(1)
    proj.SetCurrentRenderFormatAndCodec("mp4", "H264")
    tl = proj.GetCurrentTimeline()
    proj.SetRenderSettings({"SelectAllFrames": True, "TargetDir": OUT_DIR, "CustomName": NAME,
                            "FormatWidth": 540, "FormatHeight": 960, "ExportVideo": True, "ExportAudio": True,
                            "VideoQuality": 0})
    job = proj.AddRenderJob()
    out["job"] = job
    out["started"] = proj.StartRendering([job], False)
    out["timeline"] = tl.GetName()
elif STEP == "poll":
    jobs = [j for j in proj.GetRenderJobList() if j.get("OutputFilename", "").startswith(NAME) or j.get("RenderJobName", "").startswith(NAME)]
    out["jobs"] = [{"id": j["JobId"], **proj.GetRenderJobStatus(j["JobId"])} for j in jobs]
    out["rendering"] = proj.IsRenderingInProgress()
else:
    for j in proj.GetRenderJobList():
        if j.get("TargetDir") == OUT_DIR:
            proj.DeleteRenderJob(j["JobId"])
    out["restored"] = proj.LoadRenderPreset(KEEP)
    out["deleted_temp_preset"] = proj.DeleteRenderPreset(KEEP)
    out["now"] = proj.GetCurrentRenderFormatAndCodec()
result = out
