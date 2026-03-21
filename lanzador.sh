#!/bin/bash
pkill mpvpaper
sleep 0.2
nohup mpvpaper -o "loop" '*' "$1" >/dev/null 2>&1 &
