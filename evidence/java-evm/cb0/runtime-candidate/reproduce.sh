#!/bin/sh
# Rebuild and verify the frozen MC-CB0 coordinator artifact from the tracked source.
set -eu
root=$(git rev-parse --show-toplevel)
cd "$root/jvmevm/localcontinuation/cb0/runtime"
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run check
sha256sum CB0ClassCoordinator.sol CB0ClassCoordinator.init.hex CB0ClassCoordinator.runtime.hex CB0ClassCoordinator.abi.json combinedartifacts/CB0ClassCoordinator.json
