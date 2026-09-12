#!/bin/bash
set -euo pipefail
export TMPDIR="$PWD/build/java-diff-mc-cb0-parent-tmp"
e="$PWD/evidence/java-evm/cb0/parent-1ec057f00"
go test -v -count=1 -timeout=18m ./jvmevm/localcontinuation/cb0/... > "$e/test-delta-package.log" 2>&1
go vet ./jvmevm/localcontinuation/cb0/... > "$e/test-delta-vet.log" 2>&1
go test -c -trimpath -o build/java-diff-mc-cb0-bounded-relocated-1ec057f00/delta.test ./jvmevm/localcontinuation/cb0
(cd build/java-diff-mc-cb0-bounded-relocated-1ec057f00 && ./delta.test -test.v -test.run='^TestCB0Parent(ActualNewProcesses|RealDirectorySyncFailure)$' -test.timeout=2m) > "$e/test-delta-relocated.log" 2>&1
echo 'PASS: full current package + vet + relocated eight-process/actual directory-fsync test-only delta'
