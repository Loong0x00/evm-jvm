#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
"$ROOT/build-bootstrap.sh"
NODE_PATH=/home/user/evm-jvm/array-list-default-constructor/jvmevm/runtime/node_modules node "$ROOT/engine/build.js"
NODE_PATH=/home/user/evm-jvm/array-list-default-constructor/jvmevm/runtime/node_modules node "$ROOT/coordinator/build.js"
REPO=$(CDPATH= cd -- "$ROOT/../../../.." && pwd)
(cd "$REPO" && GOPROXY=off GOSUMDB=off go build -o "$ROOT/build/array-list-driver" "$ROOT/canonical-driver.go")
