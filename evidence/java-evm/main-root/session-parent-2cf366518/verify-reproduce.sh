#!/bin/sh
# Receipt verification only, no EVM execution or Java/ZIP/class parsing.
set -eu
base=${1:?usage: verify-reproduce.sh BASELINE FRESH-IGNORED-VERIFIER-BUILD}
out=${2:?}
case "$out" in build/java-diff-mc-main-root-session-parent-strict-*) ;; *) exit 2;; esac
[ ! -e "$out" ] || { echo 'refuse existing verifier output' >&2; exit 2; }
mkdir -p "$out/tmp"
out=$(cd "$out" && pwd)
export TMPDIR="$out/tmp"
cp evidence/java-evm/main-root/session-parent-2cf366518/verify_receipts.go.txt "$out/main.go"
go build -trimpath -o "$out/verify" "$out/main.go"
go vet "$out/main.go"
python3 evidence/java-evm/main-root/session-parent-2cf366518/test_parent_verifier.py "$base" "$out/verify" "$out/tests"
