#!/bin/bash

# Uses ffprobe (comes with ffmpeg) to list height and duration of video
# files and list those that are already 480 in height

# usage:
# find_480_videos.sh DIR
DIR=$1
for MOVIE in $(find $DIR -name '*.mp4'); do
  if [[ $MOVIE =~ AppleDouble ]]; then
    continue
  fi
  DETAILS=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=height,duration -of csv=p=0 "$MOVIE")
  HEIGHT=$(echo $DETAILS | cut -d, -f1)
  if ! [[ $HEIGHT == "480" ]]; then
    continue
  fi
  echo $DETAILS,$MOVIE
done