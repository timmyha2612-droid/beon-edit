#!/bin/bash
# WORK=dir [CROP_Y=750] [WIDTH=1080] [HEIGHT=1920] sheet.sh TAG -> $WORK/checks/TAG_sheet.jpg : caption band of each still, 3 columns
# Set CROP_Y to the band's top when the subtitles were moved (editors often lower the compound clip).
# WIDTH/HEIGHT = frame size from the job card Delivery line (default 1080x1920, the Beon 9:16 frame).
# CROP_Y is clamped so the 420 px band stays inside the frame (16:9 1080 high: set CROP_Y to the band, e.g. 600).
cd "${WORK:-$HOME/subs_work}/checks"
TAG="$1"
W=${WIDTH:-1080}; H=${HEIGHT:-1920}; Y=${CROP_Y:-750}
[ $((Y + 420)) -gt "$H" ] && Y=$((H - 420))
[ "$Y" -lt 0 ] && Y=0
n=$(ls ${TAG}_[0-9][0-9].png | wc -l | tr -d ' ')
rows=$(( (n + 2) / 3 ))
ffmpeg -loglevel error -y -framerate 1 -i "${TAG}_%02d.png" -vf "crop=${W}:420:0:${Y},scale=360:-2,tile=3x${rows}:padding=4:color=gray" -frames:v 1 "${TAG}_sheet.jpg"
echo "${TAG}: $n stills"
