#!/bin/bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
p="$root/evidence/java-evm/class-bridge/shared-world-parent-d76a45057"
[[ $# == 1 ]] || { echo 'usage: reproduce.sh NEW_IGNORED_WORKSPACE' >&2; exit 2; }
w=$1;[[ $w == /* ]] || w="$root/$w"
[[ ! -e $w ]] || { echo 'refusing existing workspace' >&2; exit 2; }
mkdir -p "$w/classes" "$w/gensrc" "$w/fixtures" "$w/npm"
cp "$p"/{package.json,package-lock.json} "$w/npm/"
npm ci --prefix "$w/npm" --ignore-scripts --no-audit --no-fund > "$w/npm.log"
cp "$p"/{SharedEntry.java,SharedHelper.java,Oracle.java} "$w/gensrc/"
for n in P1 P2 P3 P4 P4B; do printf 'public class %s { public static int run(int x) { return x + %s; } }\n' "$n" "${#n}" > "$w/gensrc/$n.java"; done
printf 'public class Unfinal { public static int run(int x) { return x; } }\n' > "$w/gensrc/Unfinal.java"
/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -g:none -d "$w/classes" "$w"/gensrc/*.java
/usr/lib/jvm/java-8-openjdk/bin/java -cp "$w/classes" Oracle 7 9 > "$w/oracle.log"
/usr/lib/jvm/java-8-openjdk/bin/javap -classpath "$w/classes" -c -p SharedEntry SharedHelper > "$w/javap.log"
python3 "$p/make_fixtures.py" "$w/classes" "$w/fixtures" > "$w/fixtures.log"
NODE_PATH="$w/npm/node_modules" node "$p/compile.js" "$w/coordinator.json" > "$w/compile.log"
cp "$p/driver.go.txt" "$w/driver.go"
gofmt -w "$w/driver.go"
go build -trimpath -o "$w/driver" "$w/driver.go"
go vet "$w/driver.go"
"$w/driver" setup-chain "$w/direct" "$w/coordinator.json" "$w/fixtures/shared-two.zip" 4096 7
"$w/driver" verify "$w/direct" "$w/coordinator.json"
bash "$p/run-cases.sh" "$w"
python3 "$p/verify_parent.py" "$w" "$w/parent-report.json"
sha256sum "$w/coordinator.json" "$w/driver.go" "$w/driver" "$w"/fixtures/*.zip "$w/parent-report.json" > "$w/SHA256SUMS"
