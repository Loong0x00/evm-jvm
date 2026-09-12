#!/bin/bash
set -euo pipefail
repo=$(pwd)
e="$repo/evidence/java-evm/cb0/parent-1ec057f00/bounded-final"
export TMPDIR="$repo/build/java-diff-mc-cb0-parent-tmp"
mkdir -p "$TMPDIR"
make java-mc-cb0-check > "$e/build.log" 2>&1
go test -v -count=1 -timeout=18m ./jvmevm/localcontinuation/cb0/... > "$e/package.log" 2>&1
go vet ./jvmevm/localcontinuation/cb0/... > "$e/vet.log" 2>&1
bash evidence/java-evm/cb0/runtime-candidate/reproduce-e2e.sh build/java-diff-mc-cb0-runtime-bounded-final-1ec057f00 > "$e/controller.log" 2>&1
# The previous capture rebuilt and matched the unchanged VFS0a source/artifact.
# Run its FULL tests again here without repeating that five-minute compiler job.
go test -count=1 -timeout=18m ./jvmevm/artifactstore/as0/... ./jvmevm/artifactstore/zi0/... ./jvmevm/artifactstore/di0/... ./jvmevm/localcontinuation/vfs0a/... > "$e/dependencies.log" 2>&1
mkdir -p build/java-diff-mc-cb0-bounded-relocated-1ec057f00
go test -c -trimpath -o build/java-diff-mc-cb0-bounded-relocated-1ec057f00/cb0.test ./jvmevm/localcontinuation/cb0
(cd build/java-diff-mc-cb0-bounded-relocated-1ec057f00 && ./cb0.test -test.v -test.run='^TestCB0Parent(GeneratedJavaPipeline|ActualNewProcesses|JavaPublicationFailures|ClassBoundaryAndJavaException)$' -test.timeout=18m) > "$e/relocated.log" 2>&1
git diff 23d28e13d -- core params jvmevm/artifactstore jvmevm/runtime jvmevm/localcontinuation/vfs0a > "$e/protected.diff"
test ! -s "$e/protected.diff"
python3 - "$repo/build/java-diff-mc-cb0-runtime-bounded-final-1ec057f00" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);m={x:json.loads((p/x/'durable-head.json').read_text()) for x in ['direct','q1','q7','input9']}
for x in ['direct','q1','q7']:
 assert m[x]['result']==317 and m[x]['jvmSteps']==36 and m[x]['internalSteps']==5
 for k in ['packageRoot','machineRoot','vfsRoot','resourceRoots']:assert m[x][k]==m['direct'][k]
assert [m[x]['slices'] for x in ['direct','q1','q7']]==[1,36,6]
assert m['input9']['result']==299
b=json.loads((p/'boundary/boundary-report.json').read_text());assert b['paging']['aggregate']==65536 and b['paging']['result']==9 and b['paging']['actualReadCount']==18 and max(b['paging']['actualReadSizes'])<=4096
print('STRICT: fresh final controller results, grouping and 64KiB paging match')
PY
echo 'PASS: bounded final CB0 gate; full package/dependencies; no duplicated high-input relocated workload'
