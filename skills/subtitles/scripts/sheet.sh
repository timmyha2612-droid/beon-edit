#!/bin/bash
# WORK=dir [CROP_Y=750] sheet.sh TAG -> $WORK/checks/TAG_sheet.jpg : caption band of each still, 3 columns
# Set CROP_Y to the band's top when the subtitles were moved (Tim often lowers the compound clip).
cd "${WORK:-$HOME/subs_work}/checks"
TAG="$1"
n=$(ls ${TAG}_[0-9][0-9].png | wc -l | tr -d ' ')
rows=$(( (n + 2) / 3 ))
ffmpeg -loglevel error -y -framerate 1 -i "${TAG}_%02d.png" -vf "crop=1080:420:0:${CROP_Y:-750},scale=360:140,tile=3x${rows}:padding=4:color=gray" -frames:v 1 "${TAG}_sheet.jpg"
echo "${TAG}: $n stills"
