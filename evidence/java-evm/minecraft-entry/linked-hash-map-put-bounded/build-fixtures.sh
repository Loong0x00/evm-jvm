#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p tests/classes tests/collision-classes tests/reentrant-classes \
  tests/map-equals-classes tests/view-equals-classes tests/callback-exception-classes \
  tests/equals-reentrant-classes tests/short-array-classes tests/inherited-get-classes
javac --release 8 -g:none -Xlint:-options -d tests/classes tests/src/PutProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/collision-classes \
  tests/src/CollisionRefusalProbe.java tests/src/CollisionEightProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/reentrant-classes tests/src/ReentrantRefusalProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/map-equals-classes tests/src/MapEqualsRefusalProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/view-equals-classes tests/src/ViewEqualsRefusalProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/callback-exception-classes tests/src/CallbackExceptionProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/equals-reentrant-classes tests/src/EqualsReentrantRefusalProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/short-array-classes tests/src/ShortArrayRefusalProbe.java
javac --release 8 -g:none -Xlint:-options -d tests/inherited-get-classes tests/src/InheritedGetRefusalProbe.java
java -cp tests/classes PutProbe
java -cp tests/collision-classes CollisionRefusalProbe
java -cp tests/collision-classes CollisionEightProbe
java -cp tests/reentrant-classes ReentrantRefusalProbe
java -cp tests/map-equals-classes MapEqualsRefusalProbe
java -cp tests/view-equals-classes ViewEqualsRefusalProbe
java -cp tests/callback-exception-classes CallbackExceptionProbe
java -cp tests/equals-reentrant-classes EqualsReentrantRefusalProbe
java -cp tests/short-array-classes ShortArrayRefusalProbe
java -cp tests/inherited-get-classes InheritedGetRefusalProbe
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED
cases = {
    'put-probe': ('tests/classes', ['PutProbe.class', 'ProbeKey.class']),
    'collision-refusal': ('tests/collision-classes', ['CollisionRefusalProbe.class', 'CollisionKey.class']),
    'collision-eight': ('tests/collision-classes', ['CollisionEightProbe.class', 'CollisionKey.class']),
    'reentrant-refusal': ('tests/reentrant-classes', ['ReentrantRefusalProbe.class', 'ReentrantKey.class']),
    'map-equals-refusal': ('tests/map-equals-classes', ['MapEqualsRefusalProbe.class']),
    'view-equals-refusal': ('tests/view-equals-classes', ['ViewEqualsRefusalProbe.class']),
    'callback-exception': ('tests/callback-exception-classes', ['CallbackExceptionProbe.class', 'HashThrowKey.class', 'ExistingKey.class', 'EqualsThrowKey.class']),
    'equals-reentrant-refusal': ('tests/equals-reentrant-classes', ['EqualsReentrantRefusalProbe.class', 'StableCollisionKey.class', 'EqualsReentrantKey.class']),
    'short-array-refusal': ('tests/short-array-classes', ['ShortArrayRefusalProbe.class']),
    'inherited-get-refusal': ('tests/inherited-get-classes', ['InheritedGetRefusalProbe.class']),
}
for archive, (directory, entries) in cases.items():
    with ZipFile('tests/' + archive + '.zip', 'w', compression=ZIP_STORED) as z:
        for entry in entries:
            info = ZipInfo(entry, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED
            info.external_attr = 0o100644 << 16
            z.writestr(info, (Path(directory) / entry).read_bytes())
PY
sha256sum tests/put-probe.zip tests/collision-eight.zip tests/collision-refusal.zip \
  tests/reentrant-refusal.zip tests/map-equals-refusal.zip tests/view-equals-refusal.zip \
  tests/callback-exception.zip tests/equals-reentrant-refusal.zip tests/short-array-refusal.zip tests/inherited-get-refusal.zip
