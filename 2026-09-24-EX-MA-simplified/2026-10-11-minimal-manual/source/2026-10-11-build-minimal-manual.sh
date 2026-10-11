#!/usr/bin/env bash
# Build the EX-MA minimal-build manual end to end.
#   PY      python with cadquery, trimesh, manifold3d (the project's CAD environment)
#   WORK    scratch folder for the minimal Source copy, the scene data and node_modules (three@0.160.0)
# Steps: minimal Source tree -> scene export -> figure specs -> render figures -> copy into ../figures
#        -> page HTML -> PDF. The renderer, figure runner, overlay helpers, styles and printer are shared
#        with ../../2026-10-10-assembly-manual/source/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MAN="$(dirname "$HERE")"
A="$(dirname "$MAN")/2026-10-10-assembly-manual/source"
PY="${PY:-python3}"
WORK="${WORK:-$HERE/.work}"
mkdir -p "$WORK" "$MAN/figures"
[ -d "$WORK/node_modules/three" ] || (cd "$WORK" && npm init -y >/dev/null && npm install three@0.160.0 >/dev/null)
export MINIMAL_SRC="$("$PY" "$HERE/2026-10-11-make-minimal-source.py" "$WORK/min")"
"$PY" "$HERE/2026-10-11-minimal-scene-export.py" "$MINIMAL_SRC" "$WORK/scene"
"$PY" "$HERE/2026-10-11-minimal-figure-specs.py" "$WORK/figures.json"
(cd "$WORK" && node "$A/2026-10-10-manual-figures.mjs" "$WORK/figures.json" "$WORK/scene" "$WORK/figs" "$@")
for f in "$WORK"/figs/*.png "$WORK"/figs/*.json; do cp "$f" "$MAN/figures/2026-10-11-$(basename "$f")"; done
"$PY" "$HERE/2026-10-11-build-minimal-manual.py"
(cd "$HERE" && node "$A/2026-10-10-manual-print.mjs" 2026-10-11-minimal-manual.html "$MAN/2026-10-11-ex-ma-minimal-manual.pdf")
