#!/bin/sh
# Run from repository root. This writes only the caller-selected ignored build directory.
set -eu
out=${1:?usage: reproduce.sh ignored-build-directory}
case "$out" in build/java-diff-mc-main-root-transport-*) ;; *) echo "refuse non-MR0 ignored build path" >&2; exit 2;; esac
rm -rf "$out"; mkdir -p "$out"
cp evidence/java-evm/main-root/transport-preflight/driver.go.txt "$out/main.go"
( cd "$out" && go build . )
python3 evidence/java-evm/main-root/transport-preflight/fixtures/generate-positive-exception.py "$out/fixtures" > "$out/fixture-build.json"
for q in 1 7; do
  d="$out/exception-q$q"; mkdir "$d"
  "$out/$(basename "$out")" setup-chain "$d" evidence/java-evm/main-root/preflight/coordinator/MR0MainCoordinator.json evidence/java-evm/main-root/preflight/engine/MR0MainInterpreter.json "$out/fixtures/exception.zip" "$q"
  "$out/$(basename "$out")" finish "$d" evidence/java-evm/main-root/preflight/coordinator/MR0MainCoordinator.json evidence/java-evm/main-root/preflight/engine/MR0MainInterpreter.json "$out/fixtures/exception.zip" "$q"
  "$out/$(basename "$out")" verify "$d" evidence/java-evm/main-root/preflight/coordinator/MR0MainCoordinator.json evidence/java-evm/main-root/preflight/engine/MR0MainInterpreter.json "$out/fixtures/exception.zip" "$q"
done
