#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$ROOT" rev-parse --show-toplevel)"
export NODE_PATH="$REPO/jvmevm/runtime/node_modules${NODE_PATH:+:$NODE_PATH}"
"$ROOT/build_fixture.sh"
(cd "$ROOT/engine" && node build.js)
(cd "$ROOT/coordinator" && node build.js)
mkdir -p "$ROOT/build"
(cd "$REPO" && GOPROXY=off GOSUMDB=off go build -trimpath -o "$ROOT/build/enum-map-link-driver" "$ROOT/canonical-driver.go")
python3 "$ROOT/verify_candidate.py"
