#!/bin/bash
set -euo pipefail
repo=$(pwd)
e="$repo/evidence/java-evm/cb0/parent-1ec057f00"
export TMPDIR="$repo/build/java-diff-mc-cb0-parent-tmp"
mkdir -p "$TMPDIR"
make java-mc-cb0-check > "$e/final-build.log" 2>&1
go test -v -count=1 -timeout=18m ./jvmevm/localcontinuation/cb0/... > "$e/final-package.log" 2>&1
go vet ./jvmevm/localcontinuation/cb0/... > "$e/final-vet.log" 2>&1
bash evidence/java-evm/cb0/runtime-candidate/reproduce-e2e.sh build/java-diff-mc-cb0-runtime-parent-final-1ec057f00 > "$e/final-controller.log" 2>&1
make java-mc-as0-test java-mc-zi0-test java-mc-di0-test java-mc-vfs0a-test > "$e/final-dependencies.log" 2>&1
mkdir -p build/java-diff-mc-cb0-parent-relocated-1ec057f00
go test -c -trimpath -o build/java-diff-mc-cb0-parent-relocated-1ec057f00/cb0.test ./jvmevm/localcontinuation/cb0
(cd build/java-diff-mc-cb0-parent-relocated-1ec057f00 && ./cb0.test -test.v -test.run='^TestCB0Parent' -test.timeout=18m) > "$e/final-relocated.log" 2>&1
git diff 23d28e13d -- core params jvmevm/artifactstore jvmevm/runtime jvmevm/localcontinuation/vfs0a > "$e/protected.diff"
test ! -s "$e/protected.diff"
echo 'PASS: actual CB0 build/package/vet/controller replay/AS0/ZI0/DI0/VFS0a/relocated parent and protected-code gates'
