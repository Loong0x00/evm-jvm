# Properties minimum-slice cost preflight (read-only)

This is a generated-fixture measurement handoff, not an acceptance and not a
Minecraft/original-world run.  No Solidity semantic, optimizer, ABI, quota,
artifact, or accepted-profile change is in this commit.

## Exact unchanged pin and compiler metadata

`evidence/java-evm/minecraft-entry/properties-cost-preflight/metadata/` was
built from the recovered parent source only with:

* solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer runs 200, via-IR,
  Cancun, metadata CBOR off;
* engine address `0x4d4350524f50455254494553504152454e540001`, domain
  `MC-PROPERTIES-PARENT1`;
* runtime 321590 bytes, SHA-256
  `877f35a4ac4092a7c65ab5071104413e4579ced0b69a172852db77d772aee1bb`,
  Keccak `eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7`;
* coordinator Keccak
  `4ac62a3ecc1612110cbc97779ebf760d101a33f1c85ddfb03c75d1b5478f2bae`.

The metadata build requests AST, deployed source map, function debug data,
opcodes, and optimized IR.  It **requires byte-for-byte deployed-runtime
equality** with the parent artifact before it writes metadata.  Its successful
summary records 172192 source-map entries, 456 function-debug entries and zero
generated sources.  The Solidity warnings are archived in `build.log`; they
are compiler diagnostics from unchanged source, not edits.

## Observer boundaries

`driver/properties_cost_observer_driver.go.txt` is a source-only copy of
`parent-c24d374bc/executed_smaller_driver.go.txt`.  It retains that driver's
normal public `startMain`/`resumeMain` coordinator route, normal StateDB/trie
world, AS0/ZI0/DI0 resource path, exact code checks, saved quantum, 100M gas,
25M reserve, and bounded call deadline.  It does not use private Session,
reflection, injected pages, failed-state recovery, host class evaluation, or
original inputs.

`MC_PROPERTIES_COST_OBSERVER=1` adds only Go tracer collection.  Per
coordinator call it records engine-PC opcode count/cost, a 128-entry engine-PC
ring, engine memory length growth and numeric Solidity free-pointer samples.
It immediately derives the numeric word at memory offset `0x40` and retains no
memory byte.  It records no stack, calldata, class, ZIP, resource page, raw
checkpoint, or VFS payload.  A call-depth ledger records child forwarded caps
and child gas used separately.  Consequently a CALL's forwarded cap is never
added to the engine-exclusive PC total; the all-call ledger is explicitly not
a second cost total.

The archived 4.5MiB generated refusal observation is a PC aggregate only (no
raw guest input or EVM memory).  The mapping script consumes the solc opcode
text because trailing compiler data must not be decoded as executable code.

## Generated controls and measurement

`run_generated_controls.py` recompiles only the two source fixtures in its own
directory with Java 8 `-g:none`, creates a deterministic stored ZIP, and runs
it only through public EVM APIs.  It uses a fresh absolute ignored
`build/java-diff-mc-properties-cost-*` directory and a 20-minute group deadline.
No Java oracle/guest host execution occurs.

The archived `runs/generated-controls-summary.json` proves observer OFF/ON
identity for the exact code pin, return/revert, gas, checkpoint/root and final
head fields:

* `PropertiesConstructionProbe`, q7: terminal VOID at epoch 11, 73 Java and 4
  internal steps; identical checkpoint root
  `0xdf7655d149c7831137e287c32ae89be88da2ce9b6ee382f0d3e3faf6b4941c5b`.
  The last slice used 13,120,190 gas and has a 1876-byte generated checkpoint.
* `BigPropertiesProbe`, direct q4096: ordinary reserve refusal,
  `LC0ControlError(7)`, selector `0xf15d7343`, at 73,624,662 gas.  OFF and ON
  have exactly the same 36-byte raw revert, pre/post root
  `0x48237685ff1463294202acf39b63d00582c939b3046c95cd3eebcdec27796873`,
  and unstarted epoch-0 head.  This is a generated reserve control, not the
  paused original20 slice.

For that generated refusal the observer saw 17,217,319 engine opcodes costing
73,540,465 gas; engine forwarded-call gas is zero.  Outer/nested accounting
records 12 matched calls, 1,180,739,156 forwarded cap gas and 73,576,538 child
used gas, separately.  Maximum engine memory length/free pointer were both
2,465,248 bytes; 19,270 memory growth events and 3,733 free-pointer changes
were sampled.  These are cost diagnostics, not a request to raise heap,
checkpoint, gas, reserve, frame, class, VFS, or engine limits.

## Guard identification and limitation

The source map resolves the generated refusal's terminal engine PC `115770`
(`REVERT`) to `_execute`, `MCEntryInterpreter.sol:3816:57..75`, specifically:

```
if (gasleft() <= COMMIT_RESERVE) revert LC0ControlError(7);
```

It therefore distinguishes this generated control from the separate
`_checkBudgets` (line 568) and `_commit` (line 832) reserve sites.  The mapped
function totals identify compiler-generated lowering, `_findClass`,
`_validInternalName`, `_equalsCross`, and `_execute` as the largest measured
buckets; they do not authorize a semantic optimization.

This does **not** establish which reserve guard the actual paused original20
will take.  Parent alone must apply this same unchanged observer via public
q1 `ResumeMain` to its actual last checkpoint and independently review the
last-PC/source-map evidence.  No original JAR/class/page/checkpoint/world was
opened, copied, indexed, parsed, packaged, or run here.

## Reproduction

From this worktree, with the pinned installed solc modules:

```sh
NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules \
  node evidence/java-evm/minecraft-entry/properties-cost-preflight/metadata/build_debug_metadata.js
TMPDIR="$PWD/build/java-diff-mc-properties-cost-shelltmp" \
  python3 evidence/java-evm/minecraft-entry/properties-cost-preflight/run_generated_controls.py
python3 evidence/java-evm/minecraft-entry/properties-cost-preflight/metadata/map_observation.py \
  evidence/java-evm/minecraft-entry/properties-cost-preflight/runs/big-properties-direct-refusal-observation.json \
  evidence/java-evm/minecraft-entry/properties-cost-preflight/runs/big-properties-direct-refusal-source-map.json
```
