#!/bin/bash
# Install the 5 titles in assets/ (Fluid Reveal, Fluid Reveal Words, its Hook and Kinetic versions, Beon Name
# Title) and the Auto/Resync Subtitles scripts into DaVinci Resolve (macOS paths).
# Restart Resolve (or reopen the Effects panel) afterwards.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
R="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$R/Templates/Edit/Titles" "$R/Scripts/Edit"
cp "$HERE"/assets/Fluid* "$HERE"/assets/Beon* "$R/Templates/Edit/Titles/"
cp "$HERE/scripts/Auto Subtitles.py" "$HERE/scripts/Resync Subtitles.py" "$R/Scripts/Edit/"
echo "Installed 5 titles (Fluid Reveal, Fluid Reveal Words, Fluid Reveal Words Hook, Fluid Reveal Words Kinetic, Beon Name Title) and scripts (Auto Subtitles, Resync Subtitles)."
