# Reproduction: generated-only LinkedHashMap P49 gates

Run from the repository root on the pinned local toolchain. These commands use only this candidate's generated classes/ZIPs and the accepted P48 source-only base; they do not read an original Minecraft input.

```sh
OUT=evidence/java-evm/minecraft-entry/linked-hash-map-constructor-bounded
export NODE_PATH="$PWD/jvmevm/runtime/node_modules"
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d "$OUT/classes/javac" "$OUT/bootstrap/java/util/LinkedHashMap.java"
(cd "$OUT/engine" && node build.js)
(cd "$OUT/coordinator" && node build.js)
go build -o "$OUT/tools/canonical-driver" "$OUT/tools/canonical_driver.go"
python3 "$OUT/tools/verify_candidate.py"
```

The checked-in generated ZIPs are built from trusted sources in this directory. The q1/q7/q16 worlds and selected refusal worlds are durable public-EVM evidence, not host Java results. To repeat an empty-map world, create a new directory outside an existing Session, then run `setup-chain` with `MC_ENTRY_BINDINGS=LinkedHashMapEmptyMain.class`, the two candidate artifact JSONs, `results/generated-empty-api.zip`, and the quantum. Resume by invoking `resume-one-q1` for quantum 1 or `resume-one` for other quanta, each in a fresh process, until `durable-head.json.lifecycle != 1`; then run `verify`. Store process logs and observer receipts outside the Session directory (the canonical driver checks the Session's exact root contents).

The high-index fixture archive is `results/generated-raw150-high-array.zip`; bind all 150 `.class` paths with `HighArrayMain.class` first (the exact order is sorted and recorded by the candidate manifest), run `setup-chain` at q16, resume until terminal, and run `verify`. It reaches a terminal fresh-reopened `LinkedHashMap[]` allocation/`instanceof` check with raw class count 150.

Raw `put`/inherited API tests deliberately stop on the first EVM raw refusal. Their exact immutable input ZIP, world, `resume-refusal.json` (under the sibling `reports/` directory), and q16 source/receipt summaries are pinned in `results/manifest.json` and `results/guest-api-refusal-results.json`. No raw refusal is caught or continued in guest state.
