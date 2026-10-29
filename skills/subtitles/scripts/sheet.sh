#!/bin/bash
# WORK=dir sheet.sh TAG -> $WORK/checks/TAG_sheet.jpg : caption band of each still, 3 columns
cd "${WORK:-$HOME/subs_work}/checks"
TAG="$1"
n=$(ls ${TAG}_[0-9][0-9].png | wc -l | tr -d ' ')
rows=$(( (n + 2) / 3 ))
ffmpeg -loglevel error -y -framerate 1 -i "${TAG}_%02d.png" -vf "crop=1080:420:0:750,scale=360:140,tile=3x${rows}:padding=4:color=gray" -frames:v 1 "${TAG}_sheet.jpg"
echo "${TAG}: $n stills"
