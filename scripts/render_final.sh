#!/usr/bin/env bash
# Full pipeline: Remotion master render -> two-pass loudness normalisation -> final-video.mp4
# Requires a Chromium binary in $REMOTION_BROWSER_EXECUTABLE (see README "Rendering in restricted sandboxes").
set -euo pipefail
cd "$(dirname "$0")/.."
MASTER="${MASTER:-/tmp/flaghunters-master.mp4}"
OUT="final-video.mp4"

npx remotion render src/index.ts FlagHunters "$MASTER" \
  --codec=h264 --crf=16 --pixel-format=yuv420p --audio-codec=aac --audio-bitrate=320k \
  --gl=swiftshader --chromium-options=no-sandbox,disable-dev-shm-usage

# Pass 1: measure
M=$(ffmpeg -hide_banner -nostats -i "$MASTER" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 \
  | python3 -c "import sys,json;s=sys.stdin.read();print(json.dumps(json.loads(s[s.rindex('{'):s.rindex('}')+1])))")
AF=$(python3 -c "import json,sys;j=json.loads(sys.argv[1]);print(f\"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true\")" "$M")

# Pass 2: encode the deliverable (limited-range BT.709 4:2:0, H.264 High, AAC 320k)
ffmpeg -hide_banner -loglevel error -y -i "$MASTER" -map 0:v:0 -map 0:a:0 \
  -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 19 -profile:v high -level 4.2 -tune film -movflags +faststart -r 30 \
  -c:a aac -b:a 320k -ar 48000 -af "$AF" "$OUT"
echo "wrote $OUT"
