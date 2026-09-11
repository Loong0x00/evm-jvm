#!/bin/bash
set -euo pipefail
repo=$(pwd)
e="$repo/evidence/java-evm/di0/parent-final-ac454a910"
make java-mc-di0-check > "$e/final-artifact-check.log" 2>&1
go test -v -count=1 -timeout=18m ./jvmevm/artifactstore/di0/... > "$e/final-package.log" 2>&1
go vet ./jvmevm/artifactstore/di0/... > "$e/final-vet.log" 2>&1
bash evidence/java-evm/di0/runtime-candidate/replay.sh build/java-diff-mc-di0-final-ac454a910 > "$e/final-runtime-replay.log" 2>&1
make java-mc-as0-test java-mc-zi0-test > "$e/final-dependencies.log" 2>&1
mkdir -p build/java-diff-mc-di0-final-relocated-ac454a910
go test -c -trimpath -o build/java-diff-mc-di0-final-relocated-ac454a910/di0.test ./jvmevm/artifactstore/di0
(cd build/java-diff-mc-di0-final-relocated-ac454a910 && ./di0.test -test.v -test.run='^TestDI0Parent' -test.timeout=18m) > "$e/final-relocated.log" 2>&1
make java-mc-di0-demo > "$e/final-fixture.log" 2>&1
git diff ac454a910 -- core params jvmevm/runtime jvmevm/localcontinuation jvmevm/artifactstore/as0 jvmevm/artifactstore/zi0 > "$e/protected.diff"
test ! -s "$e/protected.diff"
echo 'PASS: final pinned build/package/vet/runtime reconstruction/dependencies/relocated parent/fixture gates; protected paths unchanged'
