#!/usr/bin/env bash
# Build the EX-MA assembly manual end to end.
#   PY      python with cadquery, trimesh, manifold3d (the project's CAD environment)
#   WORK    scratch folder for the scene data (about 11 MB) and node_modules (three@0.160.0)
# Steps: scene export -> figure specs -> render figures -> copy into ../figures -> page HTML -> PDF.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MAN="$(dirname "$HERE")"
PY="${PY:-python3}"
WORK="${WORK:-$HERE/.work}"
mkdir -p "$WORK" "$MAN/figures"
[ -d "$WORK/node_modules/three" ] || (cd "$WORK" && npm init -y >/dev/null && npm install three@0.160.0 >/dev/null)
"$PY" "$HERE/2026-10-10-manual-scene-export.py" "$WORK/scene"
"$PY" "$HERE/2026-10-10-manual-figure-specs.py" "$WORK/figures.json"
(cd "$WORK" && node "$HERE/2026-10-10-manual-figures.mjs" "$WORK/figures.json" "$WORK/scene" "$WORK/figs" "$@")
for f in "$WORK"/figs/*.png "$WORK"/figs/*.json; do cp "$f" "$MAN/figures/2026-10-10-$(basename "$f")"; done
"$PY" "$HERE/2026-10-10-build-manual.py"
node "$HERE/2026-10-10-manual-print.mjs" "$HERE/2026-10-10-manual.html" "$MAN/2026-10-10-ex-ma-assembly-manual.pdf"
