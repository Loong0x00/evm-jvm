#!/bin/sh
# Controller-only EVM replay of the retained generated SharedEntry/SharedHelper fixture.
# This is not the CB0 transport acceptance gate. The workspace must be ignored and absent.
set -eu
[ "$#" = 1 ] || { echo "usage: $0 NEW_IGNORED_WORKSPACE" >&2; exit 2; }
root=$(git rev-parse --show-toplevel)
case "$1" in /*) work=$1 ;; *) work=$root/$1 ;; esac
case "$work" in "$root"/build/java-diff-mc-cb0-runtime-*) ;; *) echo "workspace must be build/java-diff-mc-cb0-runtime-*" >&2; exit 2 ;; esac
[ ! -e "$work" ] || { echo "refusing existing workspace" >&2; exit 2; }
parent=$root/evidence/java-evm/class-bridge/shared-world-parent-d76a45057
candidate=$root/evidence/java-evm/cb0/runtime-candidate
artifact=$root/jvmevm/localcontinuation/cb0/runtime/combinedartifacts/CB0ClassCoordinator.json
mkdir -p "$work/gensrc" "$work/classes" "$work/fixtures"
python3 "$candidate/adapt_parent_driver.py" "$parent/driver.go.txt" "$work/driver.go"
cp "$parent/make_fixtures.py" "$work/"
cp "$parent"/{SharedEntry.java,SharedHelper.java,Oracle.java} "$work/gensrc/"
for n in P1 P2 P3 P4 P4B; do printf 'public class %s { public static int run(int x) { return x + %s; } }\n' "$n" "${#n}" > "$work/gensrc/$n.java"; done
printf 'public class Unfinal { public static int run(int x) { return x; } }\n' > "$work/gensrc/Unfinal.java"
/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -g:none -d "$work/classes" "$work"/gensrc/*.java
/usr/lib/jvm/java-8-openjdk/bin/java -cp "$work/classes" Oracle 7 9 > "$work/oracle.log"
python3 "$work/make_fixtures.py" "$work/classes" "$work/fixtures" > "$work/fixtures.log"
go build -o "$work/driver" "$work/driver.go"
go vet "$work/driver.go"
"$work/driver" setup-chain "$work/direct" "$artifact" "$work/fixtures/shared-two.zip" 4096 7
"$work/driver" verify "$work/direct" "$artifact"
"$work/driver" setup-chain "$work/q7" "$artifact" "$work/fixtures/shared-two.zip" 7 7
"$work/driver" finish "$work/q7" "$artifact"
"$work/driver" verify "$work/q7" "$artifact"
"$work/driver" setup-chain "$work/q1" "$artifact" "$work/fixtures/shared-two.zip" 1 7
"$work/driver" negatives "$work/q1" "$artifact"
"$work/driver" resume-one "$work/q1" "$artifact" publication-probe
"$work/driver" finish "$work/q1" "$artifact"
"$work/driver" verify "$work/q1" "$artifact"
"$work/driver" setup-chain "$work/input9" "$artifact" "$work/fixtures/shared-two.zip" 4096 9
"$work/driver" verify "$work/input9" "$artifact"
"$work/driver" setup-memory "$work/memory1" "$artifact" "$work/fixtures/shared-two.zip" 1 7
"$work/driver" setup-memory "$work/memory7" "$artifact" "$work/fixtures/shared-two.zip" 7 7
"$work/driver" boundary "$work/boundary" "$artifact" "$work/fixtures/boundary-seven.zip"
printf 'CB0 controller EVM adapter replay passed: %s\n' "$work"
