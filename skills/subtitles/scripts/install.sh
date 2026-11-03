#!/bin/bash
# Install the Fluid Reveal titles and the Auto/Resync Subtitles scripts into DaVinci Resolve.
# Restart Resolve (or reopen the Effects panel) afterwards.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
R="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$R/Templates/Edit/Titles" "$R/Scripts/Edit"
cp "$HERE"/assets/Fluid* "$HERE"/assets/Beon* "$R/Templates/Edit/Titles/"
cp "$HERE/scripts/Auto Subtitles.py" "$HERE/scripts/Resync Subtitles.py" "$R/Scripts/Edit/"
echo "Installed titles (Fluid Reveal, Fluid Reveal Words) and scripts (Auto Subtitles, Resync Subtitles)."
